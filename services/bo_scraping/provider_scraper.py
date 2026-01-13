import logging
import re
import time
from typing import List, Tuple, Optional
from bs4 import BeautifulSoup
from .base_scraper import BOServiceBase
from common.models import Partner, PartnerDetail

logger = logging.getLogger("BOProviderScraper")

class BOProviderScraper(BOServiceBase):
    """Scraper pour les prestataires (Partenaires) en BO"""
    
    def search_providers(self, filters: dict = None, page: int = 1) -> Tuple[List[Partner], int, int]:
        """
        Recherche exhaustive des prestataires via filtres.
        
        Args:
            filters: Dictionnaire complet des filtres
            page: Numéro de page
        """
        self._log_separator(f"RECHERCHE PRESTATAIRES - Page {page}")
        
        # Base URL
        url_parts = [f"{self.BASE_URL}/search/partner"]
        
        # Default filters if not provided
        if not filters: filters = {}
        
        # Build URL parts
        filter_parts = self._build_filter_url_parts(filters)
        url_parts.extend(filter_parts)
                
        # Pagination
        url_parts.extend([
            f"page/{page}"
        ])
        
        full_url = "/".join(url_parts)
        
        html = self._fetch_page(full_url, f"Prestataires page {page}")
        if not html:
            return [], 0, 0
        
        return self._parse_search_results(html)
    
    def _parse_search_results(self, html: str) -> Tuple[List[Partner], int, int]:
        """Parse les résultats de recherche prestataires"""
        soup = BeautifulSoup(html, 'html.parser')
        partners = []
        
        total_results = 0
        match = re.search(r'Nombre de résultats\s*.*?\s*(\d+)', html, re.DOTALL)
        if match:
            total_results = int(match.group(1))
            
        if total_results == 0:
            # Fallback soup
            summary = soup.find('div', class_='result-summary') or soup.find('span', class_='nb-items')
            if summary:
                match_text = re.search(r'(\d+)', summary.get_text(strip=True))
                if match_text:
                    total_results = int(match_text.group(1))
        
        total_pages = (total_results + 9) // 10 if total_results > 0 else 1
        
        table = soup.find('table', class_='data-result') or soup.find('table', class_='box-result')
        if not table:
            return [], total_results, total_pages
        
        tbody = table.find('tbody')
        if not tbody:
            return [], total_results, total_pages
        
        rows = tbody.find_all('tr', class_=re.compile(r'bg-(light|dark)'))
        
        for row in rows:
            partner = self._parse_partner_row(row)
            if partner:
                partners.append(partner)
        
        return partners, total_results, total_pages
    
    def _parse_partner_row(self, row) -> Optional[Partner]:
        """Parse une ligne partenaire"""
        cells = row.find_all('td')
        if len(cells) < 5:
            return None

        partner = Partner()

        # Status class
        row_classes = row.get('class', [])
        for cls in row_classes:
            if cls not in ['bg-light', 'bg-dark']:
                partner.status = cls
                if 'active' in cls.lower(): partner.web_status = 'ACTIVE'
                break

        # Code & ID (souvent colonne 1 ou 2)
        link = row.find('a', href=re.compile(r'/partner/index/id/'))
        if link:
            partner.name = link.get_text(strip=True)
            href = link.get('href', '')
            match = re.search(r'/id/(\d+)', href)
            if match:
                partner.id = int(match.group(1))
                partner.detail_url = f"{self.BASE_URL}/partner/index/id/{partner.id}"

        # Essayer de trouver le code
        text_content = row.get_text()
        code_match = re.search(r'[A-Z0-9]{3,}', text_content)
        if code_match:
            # Simple heuristique, à affiner
            pass

        # Adresse / Ville
        city_cell = None
        for cell in cells:
            txt = cell.get_text(strip=True)
            # Code postal ou Ville ?
            if re.search(r'\d{5}', txt):
                partner.zipcode = txt
            elif len(txt) > 2 and txt.isupper() and not re.search(r'\d', txt):
                if not partner.city: partner.city = txt

        return partner

    def get_provider_detail(self, provider_id: int) -> Optional[PartnerDetail]:
        """Récupère les détails d'un prestataire"""
        self._log_separator(f"DÉTAILS PRESTATAIRE ID={provider_id}")
        
        url = f"{self.BASE_URL}/partner/index/id/{provider_id}/locale/fr"
        html = self._fetch_page(url, "Fiche prestataire")
        
        if not html:
            return None
            
        return self._parse_provider_detail(html, provider_id)

    def _parse_provider_detail(self, html: str, provider_id: int) -> Optional[PartnerDetail]:
        """Parse le détail prestataire"""
        soup = BeautifulSoup(html, 'html.parser')
        detail = PartnerDetail(id=provider_id)
        detail.detail_url = f"{self.BASE_URL}/partner/index/id/{provider_id}"
        
        h1 = soup.find('h1')
        if h1:
            detail.name = h1.get_text(strip=True)
            
        # Extraction basique des champs via inputs/selects
        # (Logique similaire aux autres scrapers)
        for inp in soup.find_all('input'):
            name = inp.get('name', '').lower()
            val = inp.get('value', '')
            if not val: continue
            
            if 'address' in name: detail.address = val
            elif 'zipcode' in name: detail.zipcode = val
            elif 'city' in name: detail.city = val
            elif 'country' in name: detail.country = val
            elif 'phone' in name: detail.phone = val
            elif 'email' in name: detail.email = val
            elif 'website' in name: detail.website = val
            elif 'code' in name and not detail.code: detail.code = val
            
        return detail
