import logging
import re
import time
import os
import tempfile
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from .base_scraper import BOServiceBase
from common.models import (
    Product, ProductDetail, ProductDescriptions, ProductCharacteristics,
    ProductMerchandising, ProductImages, Materialization
)

logger = logging.getLogger("BOBoxScraper")

class BOBoxScraper(BOServiceBase):
    """Scraper pour les produits (Boxes) et listes de produits en BO"""
    
    def search_products(self, filters: dict = None, page: int = 1) -> Tuple[List[Product], int, int]:
        """
        Recherche exhaustive des produits via filtres.
        
        Args:
            filters: Dictionnaire complet des filtres
            page: Numéro de page
        """
        self._log_separator(f"RECHERCHE PRODUITS - Page {page}")
        
        # Base URL
        url_parts = [f"{self.BASE_URL}/search/box"]
        
        # Default filters if not provided
        if not filters: filters = {}
        
        # Build URL parts from filters
        filter_parts = self._build_filter_url_parts(filters)
        url_parts.extend(filter_parts)
                
        # Pagination & Defaults
        url_parts.extend([
            "boxedShops_nullable/0",
            "in_boxedChecks_check_commissionFree/0",
            "notIn_boxedChecks_check_commissionFree/0",
            f"page/{page}"
        ])
        
        full_url = "/".join(url_parts)
        
        html = self._fetch_page(full_url, f"Recherche produits page {page}")
        if not html:
            return [], 0, 0
        
        return self._parse_search_results(html)
    
    def _parse_search_results(self, html: str) -> Tuple[List[Product], int, int]:
        """Parse les résultats de recherche"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Total
        # Total
        total_results = 0
        
        # Method 1: Robust Regex on raw HTML (handles &nbsp; and <strong>)
        # Matches "Nombre de résultats", followed by any chars (non-greedy), then digits
        match = re.search(r'Nombre de résultats\s*.*?\s*(\d+)', html, re.DOTALL)
        if match:
             total_results = int(match.group(1))

        # Method 2: Fallback using BeautifulSoup if regex fails or to be safer
        if total_results == 0:
            summary = soup.find('div', class_='result-summary') or soup.find('span', class_='nb-items')
            if summary:
                text = summary.get_text(strip=True)
                match_text = re.search(r'(\d+)', text)
                if match_text:
                    total_results = int(match_text.group(1))
        
        total_pages = (total_results + 9) // 10 if total_results > 0 else 1
        
        # Table
        table = soup.find('table', class_='box-result')
        if not table:
            return [], total_results, total_pages
        
        tbody = table.find('tbody')
        if not tbody:
            return [], total_results, total_pages
        
        rows = tbody.find_all('tr', class_=['bg-light', 'bg-dark'])
        
        for i, row in enumerate(rows):
            product = self._parse_product_row(row)
            if product:
                products.append(product)
        
        return products, total_results, total_pages
    
    def _parse_product_row(self, row) -> Optional[Product]:
        """Parse une ligne produit"""
        cells = row.find_all('td')
        if len(cells) < 10:
            return None

        product = Product()

        # ID
        checkbox = cells[1].find('input', type='checkbox') if len(cells) > 1 else None
        if checkbox:
            match = re.search(r'check(\d+)', checkbox.get('ng-model', ''))
            if match:
                product.id = int(match.group(1))

        # CODE + STATUS (Cell 2)
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/box/index/id/'))
            if code_link:
                product.code = code_link.get_text(strip=True)
                href = code_link.get('href', '')
                product.detail_url = f"{self.BASE_URL}{href}" if href else ""
                
                if not product.id:
                    id_match = re.search(r'/id/(\d+)', href)
                    if id_match:
                        product.id = int(id_match.group(1))

            parts = cells[2].get_text(separator='|', strip=True).split('|')
            if len(parts) > 1:
                product.status = parts[-1].strip()

        # NAMING (Cell 3)
        if len(cells) > 3:
            name_link = cells[3].find('a', href=re.compile(r'/box/index/id/'))
            if name_link:
                product.name = name_link.get_text(strip=True)
            parts = cells[3].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                product.product_type = parts[1].strip() if len(parts) > 1 else ""
                product.reference = parts[2].strip() if len(parts) > 2 else ""

        # WEB STATUS (Cell 4)
        if len(cells) > 4:
            web_status_text = cells[4].get_text(strip=True)
            if web_status_text and web_status_text not in ['-', '']:
                product.web_status = web_status_text

        # MODEL (Cell 5)
        if len(cells) > 5:
            product.model = cells[5].get_text(strip=True)

        # COLLECTION/VERSION (Cell 6)
        if len(cells) > 6:
            coll_text = cells[6].get_text(strip=True)
            if coll_text and coll_text not in ['-', '']:
                if '/' in coll_text:
                    parts = coll_text.split('/')
                    product.collection = parts[0].strip()
                    product.version = parts[1].strip() if len(parts) > 1 else ""
                else:
                    product.collection = coll_text

        # PUBLISHER (Cell 7)
        if len(cells) > 7:
            product.publisher = cells[7].get_text(strip=True)

        # VALIDITY (Cell 8)
        if len(cells) > 8:
            product.validity_duration = cells[8].get_text(strip=True)

        # YEAR (Cell 9)
        if len(cells) > 9:
            product.production_year = cells[9].get_text(strip=True)

        # ACTIVITIES (Cell 10)
        if len(cells) > 10:
            act_text = cells[10].get_text(strip=True)
            match = re.search(r'(\d+)\s*prestation', act_text)
            if match:
                product.activities_count = int(match.group(1))

        # PRICE (Last Cell)
        price_text = cells[-1].get_text(strip=True) if cells else ""
        match = re.search(r'([\d\s,\.]+)\s*€', price_text)
        if match:
            try:
                product.price = float(match.group(1).replace(' ', '').replace(',', '.'))
            except:
                pass

        # EAN
        for cell in cells:
            cell_text = cell.get_text(strip=True)
            ean_match = re.search(r'\b(\d{13})\b', cell_text)
            if ean_match:
                product.ean_code = ean_match.group(1)
                break

        if not product.code and not product.name:
            return None

        return product

    def get_product_detail(self, product_id: int, fetch_all_tabs: bool = True) -> Optional[ProductDetail]:
        """Récupère les détails complets d'un produit"""
        self._log_separator(f"DÉTAILS PRODUIT ID={product_id}")
        
        # Onglet 1: Présentation
        url1 = f"{self.BASE_URL}/box/index/id/{product_id}/locale/fr"
        html1 = self._fetch_page(url1, "Onglet Présentation")
        
        if not html1:
            return None
        
        detail = self._parse_product_presentation(html1, product_id)
        if not detail:
            return None
        
        if fetch_all_tabs:
            # Onglet 2: Caractéristiques
            time.sleep(0.1)
            url2 = f"{self.BASE_URL}/box/characteristic/id/{product_id}/locale/fr"
            html2 = self._fetch_page(url2, "Onglet Caractéristiques")
            if html2:
                self._parse_product_characteristics(html2, detail)
            
            # Onglet 3: Web
            time.sleep(0.1)
            url3 = f"{self.BASE_URL}/box/web/id/{product_id}/locale/fr"
            html3 = self._fetch_page(url3, "Onglet Web/Merchandising")
            if html3:
                self._parse_product_web(html3, detail)
        
        return detail

    def _parse_product_presentation(self, html: str, product_id: int) -> Optional[ProductDetail]:
        """Parse l'onglet Présentation"""
        soup = BeautifulSoup(html, 'html.parser')
        detail = ProductDetail(id=product_id)
        detail.detail_url = f"{self.BASE_URL}/box/index/id/{product_id}"

        # Nom (H1)
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)
        
        # Codes
        code_match = re.search(r'box_code/([A-Z0-9]+)', html)
        if code_match:
            detail.code = code_match.group(1)
        else:
            code_input = soup.find('input', {'name': re.compile(r'code', re.I)})
            if code_input and code_input.get('value'):
                detail.code = code_input.get('value')

        # Collection & Version
        collection_match = re.search(r'boxCollection/([A-Z0-9]+)', html)
        if collection_match:
            detail.collection = collection_match.group(1)
        version_match = re.search(r'boxVersion/([A-Z0-9_]+)', html)
        if version_match:
            detail.version = version_match.group(1)

        # Statuses
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', ''))
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '']:
                    if 'status' in name.lower() and 'web' not in name.lower():
                        detail.status = val
                    elif 'webStatus' in name or 'web_status' in name.lower():
                        detail.web_status = val
                    elif 'publisher' in name.lower():
                        detail.publisher = val

        # Price
        price_inputs = soup.find_all('input', {'name': re.compile(r'price', re.I)})
        for inp in price_inputs:
            val = inp.get('value', '')
            if val:
                try:
                    detail.price = float(val.replace(',', '.').replace(' ', ''))
                    break
                except:
                    pass

        # Images & Descriptions
        self._extract_images(soup, html, detail)
        self._extract_descriptions(soup, detail)
        self._extract_materializations(soup, detail)

        return detail

    def _extract_images(self, soup, html, detail):
        """Extrait les URL d'images"""
        # (Logique simplifiée pour images, pattern CDN)
        patterns = [
            (r'https?://[^"\'>\s]+/edito[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'edito'),
            (r'https?://[^"\'>\s]+/facing[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'facing_2d'),
            (r'https?://[^"\'>\s]+/simul[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'simul_3d'),
            (r'https?://[^"\'>\s]+/landscape[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'landscape'),
            (r'https?://[^"\'>\s]+/lengow[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'lengow'),
            (r'https?://[^"\'>\s]+/back[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'back_card'),
            (r'https?://[^"\'>\s]+/squared[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'squared'),
        ]
        for pattern, type_name in patterns:
            match = re.search(pattern, html, re.I)
            if match:
                url = match.group(0)
                setattr(detail.images, type_name, url)

    def _extract_descriptions(self, soup, detail):
        """Extrait les textareas de description"""
        textareas = soup.find_all('textarea')
        for ta in textareas:
            ta_id = ta.get('id', ta.get('name', '')).lower()
            content = ta.get_text(strip=True)
            if not content: continue
            
            # Simple mapping for FR default
            if 'targetdescription' in ta_id:
                detail.descriptions.target_description['fr'] = content
            elif 'programdescription' in ta_id:
                detail.descriptions.program_description['fr'] = content
            elif 'shortdescription' in ta_id:
                detail.descriptions.short_description['fr'] = content
            elif 'extradescription' in ta_id or 'fulldescription' in ta_id:
                detail.descriptions.full_description['fr'] = content
            elif 'catchphrase' in ta_id:
                detail.descriptions.catch_phrase['fr'] = content
    
    def _extract_materializations(self, soup, detail):
        """Extrait le tableau des matérialisations"""
        mat_table = soup.find('table', class_='box-materializations') or soup.find('table', class_=re.compile(r'material', re.I))
        if mat_table:
            rows = mat_table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    mat = Materialization()
                    mat.type = cols[0].get_text(strip=True)
                    mat.code = cols[1].get_text(strip=True)
                    mat.ean = cols[2].get_text(strip=True)
                    mat.dlu = cols[3].get_text(strip=True)
                    check = cols[4].find('input', type='checkbox')
                    mat.available = check.get('checked') is not None if check else False
                    detail.materializations.append(mat)
    
    def _parse_product_characteristics(self, html: str, detail: ProductDetail):
        """Parse l'onglet Caractéristiques"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Tags checkboxes
        for cb in soup.find_all('input', type='checkbox', checked=True):
            lbl = soup.find('label', {'for': cb.get('id')}) or cb.parent.get_text(strip=True)
            if isinstance(lbl, str):
                detail.characteristics.tags.append(lbl.strip())
            elif lbl:
                 detail.characteristics.tags.append(lbl.get_text(strip=True))

        # Weight
        w_input = soup.find('input', {'name': re.compile(r'weight', re.I)})
        if w_input:
            detail.characteristics.weight = w_input.get('value', '')

    def _parse_product_web(self, html: str, detail: ProductDetail):
        """Parse l'onglet Web/Merch"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Universe
        univ_sel = soup.find('select', {'name': re.compile(r'universe', re.I)})
        if univ_sel:
            opt = univ_sel.find('option', selected=True)
            if opt: detail.merchandising.universe = opt.get_text(strip=True)
            
        # Product Type
        type_sel = soup.find('select', {'name': re.compile(r'productType', re.I)})
        if type_sel:
            opt = type_sel.find('option', selected=True)
            if opt: detail.merchandising.product_type = opt.get_text(strip=True)

    def get_product_by_code(self, code: str, publisher: str = "FRANCE") -> Optional[Product]:
        """Recherche simple par code"""
        # URL de recherche avec filtre par code
        url = f"{self.BASE_URL}/search/box/box_code/{code}"
        if publisher:
            url += f"/publisher/{publisher}/page/1"
        
        html = self._fetch_page(url)
        if html:
            products, _, _ = self._parse_search_results(html)
            if products:
                return products[0]
        return None
