"""
Wonderbox Scraper - Classe de scraping
======================================
Scraper avec logs détaillés pour debug
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import logging
import tempfile
import os
from typing import Optional, Dict, List, Tuple

from models import (
    Product, ProductDetail, ProductDescriptions, ProductCharacteristics,
    ProductMerchandising, ProductImages, Materialization,
    Activity, ActivityDetail, ActivityLocation, ActivityCharacteristics, ActivityPricing
)

# Logger
logger = logging.getLogger("WonderboxScraper")


class WonderboxScraper:
    BASE_URL = "http://rowbx2.wonderbox.vpn"
    
    def __init__(self, cookies: Dict[str, str] = None, session: requests.Session = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
        if cookies:
            self.session.cookies.update(cookies)
            logger.info(f"Cookies configurés: {list(cookies.keys())}")
    
    def _log_separator(self, title: str = ""):
        """Affiche un séparateur dans les logs"""
        if title:
            logger.info("=" * 60)
            logger.info(f"  {title}")
            logger.info("=" * 60)
    
    def _fetch_page(self, url: str, description: str = "") -> Optional[str]:
        """Récupère une page avec logging"""
        logger.debug(f"[FETCH] {description}")
        logger.debug(f"[FETCH] URL: {url}")
        logger.debug(f"[FETCH] Cookies: {dict(self.session.cookies)}")
        
        try:
            resp = self.session.get(url, timeout=30)
            logger.debug(f"[FETCH] Status: {resp.status_code}")
            logger.debug(f"[FETCH] Taille réponse: {len(resp.text)} caractères")
            
            if resp.status_code != 200:
                logger.error(f"[FETCH] ❌ Erreur HTTP {resp.status_code}")
                return None
            
            # Vérifier si redirection vers login
            if 'auth/login' in resp.url:
                logger.error(f"[FETCH] ❌ Redirection vers login détectée!")
                return None
            
            # Vérifier le contenu pour détecter une page de login cachée
            if 'name="username"' in resp.text and 'name="password"' in resp.text:
                logger.error(f"[FETCH] ❌ Page de login détectée dans le contenu!")
                return None
            
            # Log un extrait du contenu pour debug
            logger.debug(f"[FETCH] Extrait HTML: {resp.text[:500]}...")
            
            return resp.text
            
        except requests.exceptions.Timeout:
            logger.error(f"[FETCH] ❌ Timeout")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[FETCH] ❌ Erreur connexion: {e}")
            return None
        except Exception as e:
            logger.error(f"[FETCH] ❌ Exception: {e}")
            return None
    
    def login(self, username: str, password: str) -> bool:
        """Connexion au site"""
        self._log_separator("LOGIN")
        login_url = f"{self.BASE_URL}/auth/login"
        
        try:
            resp = self.session.get(login_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            csrf_input = soup.find('input', {'name': re.compile(r'csrf|_token', re.I)})
            csrf_token = csrf_input.get('value') if csrf_input else ''
            
            data = {'username': username, 'password': password, '_token': csrf_token}
            resp = self.session.post(login_url, data=data, allow_redirects=True)
            
            success = 'logout' in resp.text.lower()
            logger.info(f"Login: {'✅ Succès' if success else '❌ Échec'}")
            return success
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def test_connection(self) -> Tuple[bool, str]:
        """Teste la connexion"""
        self._log_separator("TEST CONNEXION")
        
        try:
            logger.debug(f"Cookies actuels: {dict(self.session.cookies)}")
            resp = self.session.get(f"{self.BASE_URL}/search/box", timeout=10)
            logger.info(f"Status: {resp.status_code}")
            logger.info(f"URL finale: {resp.url}")
            logger.debug(f"Taille réponse: {len(resp.text)} caractères")
            
            if resp.status_code == 200:
                # Vérifier si c'est la page de login
                if 'auth' in resp.url.lower() and 'login' in resp.url.lower():
                    logger.warning("❌ Redirection vers login")
                    return False, "Session expirée - nouveau cookie requis"
                
                # Vérifier si le formulaire de login est dans la page
                if 'name="username"' in resp.text and 'name="password"' in resp.text:
                    logger.warning("❌ Page de login détectée")
                    return False, "Session expirée - nouveau cookie requis"
                
                # Chercher le nom d'utilisateur connecté
                if 'logout' in resp.text.lower():
                    match = re.search(r'info-login-name[^>]*>([^<]+)<', resp.text)
                    username = match.group(1).strip() if match else "inconnu"
                    logger.info(f"✅ Connecté: {username}")
                    return True, f"Connecté ({username})"
                
                # Vérifier qu'on a bien une page de recherche
                if 'box-result' in resp.text or 'search/box' in resp.text:
                    logger.info("✅ Page de recherche accessible")
                    return True, "Page accessible (utilisateur non identifié)"
                
                logger.warning("⚠️ Page chargée mais contenu inattendu")
                logger.debug(f"Extrait: {resp.text[:500]}")
                return False, "Session invalide"
            
            return False, f"Erreur HTTP {resp.status_code}"
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ Connexion impossible")
            return False, "Connexion impossible (VPN?)"
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False, str(e)
    
    # ========================================================================
    # RECHERCHE PRODUITS
    # ========================================================================
    
    def search_products(self, publisher: str = "FRANCE", web_status: str = "ACTIVE",
                       page: int = 1) -> Tuple[List[Product], int, int]:
        """Recherche les produits"""
        self._log_separator(f"RECHERCHE PRODUITS - Page {page}")
        
        url_parts = [f"{self.BASE_URL}/search/box"]
        if publisher:
            url_parts.append(f"publisher/{publisher}")
        if web_status:
            url_parts.append(f"boxPublishStatus_webStatus/{web_status}")
        url_parts.extend([
            "boxedShops_nullable/0",
            "in_boxedChecks_check_commissionFree/0",
            "notIn_boxedChecks_check_commissionFree/0",
            f"page/{page}"
        ])
        url = "/".join(url_parts)
        
        html = self._fetch_page(url, f"Recherche produits page {page}")
        if not html:
            return [], 0, 0
        
        return self._parse_search_results(html)
    
    def _parse_search_results(self, html: str) -> Tuple[List[Product], int, int]:
        """Parse les résultats de recherche"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Total
        total_results = 0
        match = re.search(r'Nombre de résultats\s*:\s*(\d+)', html)
        if match:
            total_results = int(match.group(1))
            logger.info(f"Total résultats: {total_results}")
        
        total_pages = (total_results + 9) // 10 if total_results > 0 else 1
        
        # Table
        table = soup.find('table', class_='box-result')
        if not table:
            logger.warning("Table 'box-result' non trouvée")
            return [], total_results, total_pages
        
        tbody = table.find('tbody')
        if not tbody:
            logger.warning("tbody non trouvé")
            return [], total_results, total_pages
        
        rows = tbody.find_all('tr', class_=['bg-light', 'bg-dark'])
        logger.info(f"Lignes trouvées: {len(rows)}")
        
        for i, row in enumerate(rows):
            product = self._parse_product_row(row)
            if product:
                products.append(product)
        
        logger.info(f"✅ {len(products)} produits extraits")
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
        
        # Code + Status
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/box/index/id/'))
            if code_link:
                product.code = code_link.get_text(strip=True)
                href = code_link.get('href', '')
                product.detail_url = f"{self.BASE_URL}{href}" if href else ""
            parts = cells[2].get_text(separator='|', strip=True).split('|')
            if len(parts) > 1:
                product.status = parts[-1].strip()
        
        # Nom
        if len(cells) > 3:
            name_link = cells[3].find('a', href=re.compile(r'/box/index/id/'))
            if name_link:
                product.name = name_link.get_text(strip=True)
            parts = cells[3].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                product.product_type = parts[1].strip() if len(parts) > 1 else ""
                product.reference = parts[2].strip() if len(parts) > 2 else ""
        
        # Autres
        product.model = cells[5].get_text(strip=True) if len(cells) > 5 else ""
        product.publisher = cells[7].get_text(strip=True) if len(cells) > 7 else ""
        product.validity_duration = cells[8].get_text(strip=True) if len(cells) > 8 else ""
        product.production_year = cells[9].get_text(strip=True) if len(cells) > 9 else ""
        
        # Activités
        if len(cells) > 10:
            match = re.search(r'(\d+)\s*prestation', cells[10].get_text(strip=True))
            if match:
                product.activities_count = int(match.group(1))
        
        # Prix
        price_text = cells[-1].get_text(strip=True)
        match = re.search(r'([\d\s,\.]+)\s*€', price_text)
        if match:
            try:
                product.price = float(match.group(1).replace(' ', '').replace(',', '.'))
            except:
                pass
        country_match = re.search(r'\(([^)]+)\)', price_text)
        if country_match:
            product.price_country = country_match.group(1).strip()
        
        if not product.code and not product.name:
            return None
        
        return product
    
    def get_all_products(self, publisher: str = "FRANCE", web_status: str = "ACTIVE",
                        max_pages: int = None, progress_callback=None) -> List[Product]:
        """Récupère tous les produits"""
        all_products = []
        products, total, total_pages = self.search_products(publisher, web_status, 1)
        all_products.extend(products)
        
        if progress_callback:
            progress_callback(1, total_pages, len(all_products), total)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        for page in range(2, total_pages + 1):
            products, _, _ = self.search_products(publisher, web_status, page)
            all_products.extend(products)
            if progress_callback:
                progress_callback(page, total_pages, len(all_products), total)
            time.sleep(0.3)
        
        return all_products
    
    # ========================================================================
    # DÉTAILS PRODUIT
    # ========================================================================
    
    def get_product_detail(self, product_id: int, fetch_all_tabs: bool = True) -> Optional[ProductDetail]:
        """Récupère les détails complets d'un produit"""
        self._log_separator(f"DÉTAILS PRODUIT ID={product_id}")
        
        # Onglet 1: Présentation
        url1 = f"{self.BASE_URL}/box/index/id/{product_id}/locale/fr"
        html1 = self._fetch_page(url1, "Onglet Présentation")
        
        if not html1:
            logger.error("❌ Impossible de charger l'onglet Présentation")
            return None
        
        # Sauvegarder pour debug
        debug_file = os.path.join(tempfile.gettempdir(), f"debug_product_{product_id}_tab1.html")
        try:
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html1)
            logger.debug(f"HTML sauvegardé: {debug_file}")
        except Exception as e:
            logger.debug(f"Impossible de sauvegarder debug: {e}")
        
        detail = self._parse_product_presentation(html1, product_id)
        
        if not detail:
            logger.error("❌ Échec parsing onglet Présentation")
            return None
        
        logger.info(f"✅ Présentation: code={detail.code}, name={detail.name[:30]}...")
        
        if fetch_all_tabs:
            # Onglet 2: Caractéristiques
            time.sleep(0.1)
            url2 = f"{self.BASE_URL}/box/characteristic/id/{product_id}/locale/fr"
            html2 = self._fetch_page(url2, "Onglet Caractéristiques")
            if html2:
                self._parse_product_characteristics(html2, detail)
                logger.info(f"✅ Caractéristiques: durations={detail.characteristics.durations}")
            
            # Onglet 3: Web
            time.sleep(0.1)
            url3 = f"{self.BASE_URL}/box/web/id/{product_id}/locale/fr"
            html3 = self._fetch_page(url3, "Onglet Web/Merchandising")
            if html3:
                self._parse_product_web(html3, detail)
                logger.info(f"✅ Merchandising: universe={detail.merchandising.universe}, type={detail.merchandising.product_type}")
        
        return detail
    
    def _parse_product_presentation(self, html: str, product_id: int) -> Optional[ProductDetail]:
        """Parse l'onglet Présentation"""
        logger.debug("[PARSE] Début parsing Présentation")
        logger.debug(f"[PARSE] Taille HTML: {len(html)} caractères")
        soup = BeautifulSoup(html, 'html.parser')
        
        detail = ProductDetail(id=product_id)
        detail.detail_url = f"{self.BASE_URL}/box/index/id/{product_id}"
        
        # Vérifier qu'on est bien sur une page produit
        # Chercher des éléments spécifiques à la page produit
        box_form = soup.find('form', id=re.compile(r'box', re.I))
        box_details = soup.find(id=re.compile(r'boxDetails', re.I))
        
        logger.debug(f"[PARSE] box_form trouvé: {box_form is not None}")
        logger.debug(f"[PARSE] box_details trouvé: {box_details is not None}")
        
        # Lister tous les formulaires pour debug
        forms = soup.find_all('form')
        logger.debug(f"[PARSE] Formulaires trouvés: {[f.get('id', f.get('name', 'unnamed')) for f in forms]}")
        
        # Lister tous les h1, h2 pour debug
        h1s = soup.find_all('h1')
        h2s = soup.find_all('h2')
        logger.debug(f"[PARSE] H1 trouvés: {[h.get_text(strip=True)[:50] for h in h1s]}")
        logger.debug(f"[PARSE] H2 trouvés: {[h.get_text(strip=True)[:50] for h in h2s]}")
        
        # Nom depuis h1
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)
            logger.debug(f"[PARSE] Nom (h1): {detail.name}")
        else:
            logger.warning("[PARSE] ⚠️ h1 non trouvé")
        
        # Si le nom est le titre du site, on n'est pas sur la bonne page
        if detail.name and "Gestion des prestations" in detail.name:
            logger.error("[PARSE] ❌ Page produit non chargée - titre du site détecté!")
            logger.error("[PARSE] ❌ Session probablement expirée ou cookie invalide")
            return None
        
        # Code depuis les liens navigation
        code_match = re.search(r'box_code/([A-Z0-9]+)', html)
        if code_match:
            detail.code = code_match.group(1)
            logger.debug(f"[PARSE] Code: {detail.code}")
        else:
            # Fallback: chercher dans les inputs
            code_input = soup.find('input', {'name': re.compile(r'code', re.I)})
            if code_input and code_input.get('value'):
                detail.code = code_input.get('value')
                logger.debug(f"[PARSE] Code (input): {detail.code}")
            else:
                logger.warning("[PARSE] ⚠️ Code non trouvé dans les liens ni inputs")
        
        # Collection et Version
        collection_match = re.search(r'boxCollection/([A-Z0-9]+)', html)
        if collection_match:
            detail.collection = collection_match.group(1)
            logger.debug(f"[PARSE] Collection: {detail.collection}")
        
        version_match = re.search(r'boxVersion/([A-Z0-9_]+)', html)
        if version_match:
            detail.version = version_match.group(1)
            logger.debug(f"[PARSE] Version: {detail.version}")
        
        # Modèle depuis spans .code (format XX99)
        for span in soup.find_all('span', class_='code'):
            text = span.get_text(strip=True)
            if re.match(r'^[A-Z]{2}\d{2}$', text):
                detail.model = text
                logger.debug(f"[PARSE] Modèle: {detail.model}")
                break
        
        # Descriptions depuis textareas
        logger.debug("[PARSE] Recherche des textareas...")
        textareas = soup.find_all('textarea')
        logger.debug(f"[PARSE] {len(textareas)} textareas trouvés")
        
        # Lister les noms des textareas pour debug
        ta_names = [ta.get('id', ta.get('name', 'unnamed')) for ta in textareas]
        logger.debug(f"[PARSE] Noms textareas: {ta_names[:10]}...")  # Premiers 10
        
        bullet_points = []
        for ta in textareas:
            ta_id = ta.get('id', ta.get('name', ''))
            content = ta.get_text(strip=True)
            
            if not content:
                continue
            
            # Nettoyer HTML
            content_clean = re.sub(r'<[^>]+>', ' ', content)
            content_clean = re.sub(r'\s+', ' ', content_clean).strip()
            
            # Langue
            lang_match = re.search(r'_([a-z]{2}(?:_[A-Z]{2})?)$', ta_id)
            lang = lang_match.group(1) if lang_match else 'fr'
            
            logger.debug(f"[PARSE] Textarea {ta_id}: {len(content_clean)} chars")
            
            if 'targetDescription' in ta_id:
                detail.descriptions.target_description[lang] = content_clean
                if lang == 'fr' and content_clean:
                    bullet_points.append(content_clean)
            elif 'programDescription' in ta_id:
                detail.descriptions.program_description[lang] = content_clean
                if lang == 'fr' and content_clean:
                    bullet_points.append(content_clean)
            elif 'shortDescription' in ta_id:
                detail.descriptions.short_description[lang] = content_clean
            elif 'extraDescription' in ta_id:
                detail.descriptions.full_description[lang] = content_clean
            elif 'catchPhrase' in ta_id:
                detail.descriptions.catch_phrase[lang] = content_clean
            elif 'videoLink' in ta_id:
                detail.descriptions.video_link[lang] = content_clean
            elif 'whyYouWillLoveIt' in ta_id:
                detail.descriptions.why_you_will_love[lang] = content_clean
            elif 'presentation_title' in ta_id or 'presentationTitle' in ta_id:
                detail.descriptions.title[lang] = content_clean
        
        detail.descriptions.bullet_points = bullet_points[:4]
        logger.debug(f"[PARSE] Bullet points: {len(detail.descriptions.bullet_points)}")
        
        # Matérialisations
        logger.debug("[PARSE] Recherche matérialisations...")
        mat_table = soup.find('table', class_='box-materializations')
        if mat_table:
            logger.debug("[PARSE] Table box-materializations trouvée")
            current_mat = None
            
            for row in mat_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    first = cells[0].get_text(strip=True)
                    second = cells[1].get_text(strip=True)
                    
                    if first in ['Rematerialisé', 'Dématerialisé', 'Échange']:
                        dlu_match = re.search(r'DLU\s*(glissante|fixe)?\s*:?\s*(\d+)\s*mois', second)
                        current_mat = Materialization(
                            type=first,
                            dlu=f"{dlu_match.group(2)} mois" if dlu_match else "",
                            dlu_type=dlu_match.group(1) if dlu_match and dlu_match.group(1) else ""
                        )
                        logger.debug(f"[PARSE] Mat type: {first}")
                    elif first == 'Available' and current_mat:
                        current_mat.available = second.lower() == 'oui'
                    elif current_mat and re.match(r'^[A-Z]{2}[A-Z0-9]+', first):
                        current_mat.code = first
                        if re.match(r'^\d{13}$', second):
                            current_mat.ean = second
                        detail.materializations.append(current_mat)
                        logger.debug(f"[PARSE] Mat ajoutée: {current_mat.type} - {current_mat.code}")
                        current_mat = None
        else:
            logger.warning("[PARSE] ⚠️ Table box-materializations non trouvée")
            # Lister toutes les tables pour debug
            tables = soup.find_all('table')
            logger.debug(f"[PARSE] Tables trouvées: {[t.get('class', ['unnamed']) for t in tables]}")
        
        logger.debug(f"[PARSE] Matérialisations: {len(detail.materializations)}")
        
        # EAN codes
        for span in soup.find_all('span', class_='code'):
            text = span.get_text(strip=True)
            if text and text not in detail.ean_codes:
                detail.ean_codes.append(text)
        logger.debug(f"[PARSE] EAN codes: {detail.ean_codes}")
        
        return detail
    
    def _parse_product_characteristics(self, html: str, detail: ProductDetail):
        """Parse l'onglet Caractéristiques"""
        logger.debug("[PARSE] Parsing Caractéristiques")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Durées (nuits) - checkboxes cochées
        for cb in soup.find_all('input', {'name': 'boxDetails_durations[]'}):
            if cb.get('checked'):
                value = cb.get('value', '')
                if value:
                    detail.characteristics.durations.append(value)
                    logger.debug(f"[PARSE] Durée: {value}")
        
        # Textareas pour meta
        for ta in soup.find_all('textarea'):
            ta_id = ta.get('id', '')
            content = ta.get_text(strip=True)
            if not content:
                continue
            
            lang_match = re.search(r'_([a-z]{2}(?:_[A-Z]{2})?)$', ta_id)
            lang = lang_match.group(1) if lang_match else 'fr'
            
            if 'metaTitle' in ta_id:
                detail.characteristics.meta_title[lang] = content
            elif 'metaKeywords' in ta_id:
                detail.characteristics.meta_keywords[lang] = content
            elif 'metaDescription' in ta_id:
                detail.characteristics.meta_description[lang] = content
    
    def _parse_product_web(self, html: str, detail: ProductDetail):
        """Parse l'onglet Web (Merchandising)"""
        logger.debug("[PARSE] Parsing Web/Merchandising")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Selects
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', ''))
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '']:
                    if 'productType' in name:
                        detail.merchandising.product_type = val
                        logger.debug(f"[PARSE] productType: {val}")
                    elif 'universe' in name:
                        detail.merchandising.universe = val
                        logger.debug(f"[PARSE] universe: {val}")
                    elif 'pictogram' in name:
                        detail.merchandising.pictogram = val
                        logger.debug(f"[PARSE] pictogram: {val}")
        
        # Checkboxes cochées
        for cb in soup.find_all('input', type='checkbox', checked=True):
            name = cb.get('name', '')
            value = cb.get('value', '')
            
            if 'boxThematics' in name:
                parent = cb.parent
                label = parent.get_text(strip=True) if parent else value
                detail.merchandising.thematics.append(label)
            elif 'targetTypes' in name:
                detail.merchandising.target_types.append(value)
            elif 'targetAges' in name:
                detail.merchandising.target_ages.append(value)
            elif 'targetNumbers' in name:
                detail.merchandising.target_numbers.append(value)
        
        logger.debug(f"[PARSE] Thematics: {detail.merchandising.thematics}")
        logger.debug(f"[PARSE] Target types: {detail.merchandising.target_types}")
    
    # ========================================================================
    # ACTIVITÉS
    # ========================================================================
    
    def search_activities(self, box_code: str, publisher: str = "FRANCE",
                         web_status: str = "ACTIVE", page: int = 1) -> Tuple[List[Activity], int, int]:
        """Recherche les activités d'un produit"""
        self._log_separator(f"RECHERCHE ACTIVITÉS - {box_code} - Page {page}")
        
        url_parts = [
            f"{self.BASE_URL}/search/activity",
            f"in_compensableActivities_check_boxedChecks_box_code/{box_code}"
        ]
        if publisher:
            url_parts.append(f"publisher/{publisher}")
        if web_status:
            url_parts.append(f"boxPublishStatus_webStatus/{web_status}")
        url_parts.extend([
            "boxedShops_nullable/0",
            "in_boxedChecks_check_commissionFree/0",
            "notIn_boxedChecks_check_commissionFree/0",
            f"page/{page}"
        ])
        
        html = self._fetch_page("/".join(url_parts), f"Activités {box_code} page {page}")
        if not html:
            return [], 0, 0
        
        return self._parse_activities_results(html)
    
    def _parse_activities_results(self, html: str) -> Tuple[List[Activity], int, int]:
        """Parse les résultats activités"""
        soup = BeautifulSoup(html, 'html.parser')
        activities = []
        
        total_results = 0
        match = re.search(r'Nombre de résultats\s*:\s*(\d+)', html)
        if match:
            total_results = int(match.group(1))
            logger.info(f"Total activités: {total_results}")
        
        total_pages = (total_results + 9) // 10 if total_results > 0 else 1
        
        table = soup.find('table', class_='data-result')
        if not table:
            logger.warning("Table 'data-result' non trouvée")
            return [], total_results, total_pages
        
        tbody = table.find('tbody')
        if not tbody:
            return [], total_results, total_pages
        
        rows = tbody.find_all('tr', class_=re.compile(r'bg-(light|dark)'))
        logger.info(f"Lignes activités: {len(rows)}")
        
        for row in rows:
            activity = self._parse_activity_row(row)
            if activity:
                activities.append(activity)
        
        logger.info(f"✅ {len(activities)} activités extraites")
        return activities, total_results, total_pages
    
    def _parse_activity_row(self, row) -> Optional[Activity]:
        """Parse une ligne activité"""
        cells = row.find_all('td')
        if len(cells) < 7:
            return None
        
        activity = Activity()
        
        # Statut depuis classe
        for cls in row.get('class', []):
            if cls not in ['bg-light', 'bg-dark']:
                activity.status = cls
                break
        
        # Code et ID
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/activity/index/id/'))
            if code_link:
                activity.code = code_link.get_text(strip=True)
                match = re.search(r'/id/(\d+)', code_link.get('href', ''))
                if match:
                    activity.id = int(match.group(1))
                    activity.detail_url = f"{self.BASE_URL}/activity/index/id/{activity.id}"
        
        # Nom, type, cible
        if len(cells) > 5:
            name_link = cells[5].find('a', href=re.compile(r'/activity/index/id/'))
            if name_link:
                activity.name = name_link.get_text(strip=True)
            parts = cells[5].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                activity.activity_type = parts[1].strip()
            if len(parts) >= 4:
                activity.target = parts[3].strip()
        
        # Location
        if len(cells) > 6:
            loc_link = cells[6].find('a', href=re.compile(r'/location/index/id/'))
            if loc_link:
                activity.location_name = loc_link.get_text(strip=True)
            parts = cells[6].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 5:
                activity.location_address = parts[1].strip()
                activity.location_zipcode = parts[2].strip()
                activity.location_city = parts[3].strip()
                activity.location_country = parts[4].strip()
        
        # Prix
        if len(cells) > 7:
            price_text = cells[7].get_text(strip=True)
            match = re.search(r'([\d\s,\.]+)\s*€', price_text)
            if match:
                try:
                    activity.price = float(match.group(1).replace(' ', '').replace(',', '.'))
                except:
                    pass
            country_match = re.search(r'\(([^)]+)\)', price_text)
            if country_match:
                activity.price_countries = country_match.group(1).strip()
        
        if not activity.code and not activity.name:
            return None
        
        return activity
    
    def get_activity_detail(self, activity_id: int, fetch_all_tabs: bool = True) -> Optional[ActivityDetail]:
        """Récupère les détails complets d'une activité"""
        self._log_separator(f"DÉTAILS ACTIVITÉ ID={activity_id}")
        
        url1 = f"{self.BASE_URL}/activity/index/id/{activity_id}/locale/fr"
        html1 = self._fetch_page(url1, "Onglet Présentation activité")
        
        if not html1:
            logger.error("❌ Impossible de charger l'onglet Présentation")
            return None
        
        # Debug
        debug_file = os.path.join(tempfile.gettempdir(), f"debug_activity_{activity_id}_tab1.html")
        try:
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html1)
            logger.debug(f"HTML sauvegardé: {debug_file}")
        except Exception as e:
            logger.debug(f"Impossible de sauvegarder debug: {e}")
        
        detail = self._parse_activity_presentation(html1, activity_id)
        
        if not detail:
            logger.error("❌ Échec parsing Présentation activité")
            return None
        
        logger.info(f"✅ Présentation: code={detail.code}, name={detail.name[:30]}...")
        
        if fetch_all_tabs:
            time.sleep(0.1)
            url2 = f"{self.BASE_URL}/activity/characteristic/id/{activity_id}/locale/fr"
            html2 = self._fetch_page(url2, "Onglet Caractéristiques activité")
            if html2:
                self._parse_activity_characteristics(html2, detail)
                logger.info(f"✅ Caractéristiques: duration={detail.characteristics.duration}")
        
        return detail
    
    def _parse_activity_presentation(self, html: str, activity_id: int) -> Optional[ActivityDetail]:
        """Parse l'onglet Présentation d'une activité"""
        logger.debug("[PARSE] Parsing Présentation activité")
        soup = BeautifulSoup(html, 'html.parser')
        
        detail = ActivityDetail(id=activity_id)
        detail.detail_url = f"{self.BASE_URL}/activity/index/id/{activity_id}"
        
        # Nom depuis h1
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)
            logger.debug(f"[PARSE] Nom: {detail.name}")
        
        # Code depuis liens
        for a in soup.find_all('a', href=re.compile(r'/activity/index/id/')):
            text = a.get_text(strip=True)
            if re.match(r'^[A-Z0-9]{5,}$', text):
                detail.code = text
                logger.debug(f"[PARSE] Code: {detail.code}")
                break
        
        # Si pas trouvé, chercher dans le HTML brut
        if not detail.code:
            code_match = re.search(r'>([A-Z][A-Z0-9]{5,})</a>', html)
            if code_match:
                detail.code = code_match.group(1)
                logger.debug(f"[PARSE] Code (fallback): {detail.code}")
        
        # Location depuis les liens
        loc_link = soup.find('a', href=re.compile(r'/location/index/id/'))
        if loc_link:
            detail.location.name = loc_link.get_text(strip=True)
            match = re.search(r'/id/(\d+)', loc_link.get('href', ''))
            if match:
                detail.location.id = int(match.group(1))
            logger.debug(f"[PARSE] Location: {detail.location.name}")
        
        return detail
    
    def _parse_activity_characteristics(self, html: str, detail: ActivityDetail):
        """Parse l'onglet Caractéristiques d'une activité"""
        logger.debug("[PARSE] Parsing Caractéristiques activité")
        soup = BeautifulSoup(html, 'html.parser')
        
        # Selects
        for select in soup.find_all('select'):
            name = select.get('name', '')
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '', 'Aucun']:
                    if 'duration' in name.lower():
                        detail.characteristics.duration = val
                        logger.debug(f"[PARSE] Duration: {val}")
                    elif 'roomType' in name:
                        detail.characteristics.room_type = val
        
        # Inputs
        for inp in soup.find_all('input', type='text'):
            name = inp.get('name', '')
            value = inp.get('value', '')
            if value:
                if 'weight' in name.lower():
                    detail.characteristics.weight = value
                    logger.debug(f"[PARSE] Weight: {value}")
        
        # Checkboxes
        for cb in soup.find_all('input', type='checkbox', checked=True):
            name = cb.get('name', '')
            value = cb.get('value', '')
            
            if 'ageBrackets' in name:
                detail.characteristics.age_brackets.append(value)
            elif 'hotelService' in name:
                detail.characteristics.hotel_service = True
            elif 'manualCheckAllowed' in name:
                detail.characteristics.manual_check_allowed = True
            elif 'reservationRequired' in name:
                detail.characteristics.reservation_required = True
        
        logger.debug(f"[PARSE] Age brackets: {detail.characteristics.age_brackets}")
    
    def get_all_activities_for_product(self, box_code: str, publisher: str = "FRANCE",
                                       web_status: str = "ACTIVE") -> List[Activity]:
        """Récupère toutes les activités d'un produit"""
        all_activities = []
        activities, total, total_pages = self.search_activities(box_code, publisher, web_status, 1)
        all_activities.extend(activities)
        
        for page in range(2, total_pages + 1):
            activities, _, _ = self.search_activities(box_code, publisher, web_status, page)
            all_activities.extend(activities)
            time.sleep(0.2)
        
        return all_activities
    
    # ========================================================================
    # MÉTHODES COMBINÉES
    # ========================================================================
    
    def get_all_products_with_details(self, publisher: str = "FRANCE", web_status: str = "ACTIVE",
                                      max_pages: int = None, include_activities: bool = False,
                                      include_activity_details: bool = False,
                                      progress_callback=None) -> List[Product]:
        """Récupère tous les produits avec leurs détails"""
        self._log_separator("SCRAPING COMPLET")
        
        all_products = []
        products, total, total_pages = self.search_products(publisher, web_status, 1)
        all_products.extend(products)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        for page in range(2, total_pages + 1):
            prods, _, _ = self.search_products(publisher, web_status, page)
            all_products.extend(prods)
            time.sleep(0.3)
        
        logger.info(f"✅ {len(all_products)} produits, chargement des détails...")
        
        for i, product in enumerate(all_products):
            if progress_callback:
                progress_callback(i + 1, len(all_products), product.code, "détails")
            
            if product.id:
                product.details = self.get_product_detail(product.id)
                time.sleep(0.2)
            
            if include_activities and product.code and product.activities_count > 0:
                if progress_callback:
                    progress_callback(i + 1, len(all_products), product.code, "activités")
                product.activities = self.get_all_activities_for_product(product.code, publisher, web_status)
                
                if include_activity_details and product.activities:
                    for act in product.activities:
                        if act.id:
                            act.details = self.get_activity_detail(act.id)
                            time.sleep(0.1)
                
                time.sleep(0.2)
        
        return all_products
