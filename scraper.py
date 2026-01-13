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
    Activity, ActivityDetail, ActivityLocation, ActivityCharacteristics, ActivityPricing,
    ActivityDescriptions
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
        """Connexion au site via l'API JSON"""
        self._log_separator("LOGIN")
        login_url = f"{self.BASE_URL}/json/auth/adminauth"

        try:
            # Le formulaire Rowbx utilise 'login' et 'password'
            data = {'login': username, 'password': password}

            # POST en JSON vers l'API d'authentification
            resp = self.session.post(login_url, data=data, allow_redirects=True)
            logger.debug(f"Login response status: {resp.status_code}")
            logger.debug(f"Login response URL: {resp.url}")

            # Vérifier la réponse JSON si possible
            try:
                json_resp = resp.json()
                logger.debug(f"Login JSON response: {json_resp}")
                # Si la réponse contient une erreur ou un statut d'échec
                if json_resp.get('error') or json_resp.get('success') == False:
                    logger.warning(f"Login échoué: {json_resp.get('message', 'Erreur inconnue')}")
                    return False
            except ValueError:
                # Pas de JSON, vérifier le HTML
                pass

            # Vérifier si on est redirigé vers une page authentifiée
            # ou si la session contient un cookie de session valide
            if resp.status_code == 200:
                # Tester la connexion pour confirmer
                is_connected, msg = self.test_connection()
                if is_connected:
                    logger.info(f"Login: ✅ Succès - {msg}")
                    return True

            logger.warning("Login: ❌ Échec - session non établie")
            return False
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
        """Parse une ligne produit - Extraction MAXIMALE"""
        cells = row.find_all('td')
        if len(cells) < 10:
            return None

        product = Product()

        # ========== ID ==========
        checkbox = cells[1].find('input', type='checkbox') if len(cells) > 1 else None
        if checkbox:
            match = re.search(r'check(\d+)', checkbox.get('ng-model', ''))
            if match:
                product.id = int(match.group(1))

        # ========== CODE + STATUS ==========
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/box/index/id/'))
            if code_link:
                product.code = code_link.get_text(strip=True)
                href = code_link.get('href', '')
                product.detail_url = f"{self.BASE_URL}{href}" if href else ""

                # Extraire l'ID depuis l'URL si pas déjà trouvé
                if not product.id:
                    id_match = re.search(r'/id/(\d+)', href)
                    if id_match:
                        product.id = int(id_match.group(1))

            parts = cells[2].get_text(separator='|', strip=True).split('|')
            if len(parts) > 1:
                product.status = parts[-1].strip()

        # ========== NOM + TYPE + RÉFÉRENCE ==========
        if len(cells) > 3:
            name_link = cells[3].find('a', href=re.compile(r'/box/index/id/'))
            if name_link:
                product.name = name_link.get_text(strip=True)
            parts = cells[3].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                product.product_type = parts[1].strip() if len(parts) > 1 else ""
                product.reference = parts[2].strip() if len(parts) > 2 else ""

        # ========== WEB STATUS (cellule 4 souvent) ==========
        if len(cells) > 4:
            web_status_text = cells[4].get_text(strip=True)
            if web_status_text and web_status_text not in ['-', '']:
                product.web_status = web_status_text

        # ========== MODÈLE ==========
        if len(cells) > 5:
            product.model = cells[5].get_text(strip=True)

        # ========== COLLECTION/VERSION (cellule 6 parfois) ==========
        if len(cells) > 6:
            coll_text = cells[6].get_text(strip=True)
            if coll_text and coll_text not in ['-', '']:
                # Peut contenir collection/version
                if '/' in coll_text:
                    parts = coll_text.split('/')
                    product.collection = parts[0].strip()
                    product.version = parts[1].strip() if len(parts) > 1 else ""
                else:
                    product.collection = coll_text

        # ========== PUBLISHER ==========
        if len(cells) > 7:
            product.publisher = cells[7].get_text(strip=True)

        # ========== VALIDITÉ ==========
        if len(cells) > 8:
            product.validity_duration = cells[8].get_text(strip=True)

        # ========== ANNÉE PRODUCTION ==========
        if len(cells) > 9:
            product.production_year = cells[9].get_text(strip=True)

        # ========== ACTIVITÉS ==========
        if len(cells) > 10:
            act_text = cells[10].get_text(strip=True)
            match = re.search(r'(\d+)\s*prestation', act_text)
            if match:
                product.activities_count = int(match.group(1))

        # ========== PRIX ET PAYS ==========
        price_text = cells[-1].get_text(strip=True) if cells else ""
        match = re.search(r'([\d\s,\.]+)\s*€', price_text)
        if match:
            try:
                product.price = float(match.group(1).replace(' ', '').replace(',', '.'))
            except:
                pass

        # Extraire tous les pays avec prix
        country_matches = re.findall(r'([\d\s,\.]+)\s*€\s*\(([^)]+)\)', price_text)
        for price_str, country in country_matches:
            try:
                price_val = float(price_str.replace(' ', '').replace(',', '.'))
                product.prices_by_country[country.strip()] = price_val
            except:
                pass

        # Premier pays trouvé
        country_match = re.search(r'\(([^)]+)\)', price_text)
        if country_match:
            product.price_country = country_match.group(1).strip()

        # ========== EAN depuis la ligne (si présent) ==========
        for cell in cells:
            cell_text = cell.get_text(strip=True)
            ean_match = re.search(r'\b(\d{13})\b', cell_text)
            if ean_match:
                product.ean_code = ean_match.group(1)
                break

        # ========== CLASSE DE LIGNE POUR INFOS SUPPLÉMENTAIRES ==========
        row_classes = row.get('class', [])
        for cls in row_classes:
            if cls not in ['bg-light', 'bg-dark']:
                # Peut indiquer un statut spécial
                if 'active' in cls.lower():
                    product.web_status = product.web_status or 'ACTIVE'
                elif 'archived' in cls.lower():
                    product.web_status = product.web_status or 'ARCHIVED'

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
    # RECHERCHE PRODUIT PAR CODE
    # ========================================================================

    def get_product_by_code(self, code: str, publisher: str = "FRANCE") -> Optional[Product]:
        """Recherche un produit par son code (ex: B33O01)"""
        self._log_separator(f"RECHERCHE PRODUIT PAR CODE: {code}")

        # URL de recherche avec filtre par code
        url = f"{self.BASE_URL}/search/box/box_code/{code}"
        if publisher:
            url += f"/publisher/{publisher}/page/1"

        html = self._fetch_page(url, f"Recherche produit code={code}")
        if not html:
            return None

        products, total, _ = self._parse_search_results(html)

        if products:
            # Trouver le produit exact
            for p in products:
                if p.code == code:
                    logger.info(f"✅ Produit trouvé: {p.code} (ID={p.id})")
                    return p

            # Si pas de match exact, retourner le premier
            logger.info(f"✅ Produit trouvé (premier résultat): {products[0].code} (ID={products[0].id})")
            return products[0]

        logger.warning(f"❌ Aucun produit trouvé pour code={code}")
        return None

    def get_product_detail_by_code(self, code: str, publisher: str = "FRANCE",
                                    fetch_all_tabs: bool = True) -> Optional[ProductDetail]:
        """Récupère les détails complets d'un produit à partir de son code"""
        product = self.get_product_by_code(code, publisher)
        if product and product.id:
            return self.get_product_detail(product.id, fetch_all_tabs)
        return None

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
        """Parse l'onglet Présentation - Extraction MAXIMALE des données"""
        logger.debug("[PARSE] Début parsing Présentation")
        logger.debug(f"[PARSE] Taille HTML: {len(html)} caractères")
        soup = BeautifulSoup(html, 'html.parser')

        detail = ProductDetail(id=product_id)
        detail.detail_url = f"{self.BASE_URL}/box/index/id/{product_id}"

        # Vérifier qu'on est bien sur une page produit
        box_form = soup.find('form', id=re.compile(r'box', re.I))
        box_details = soup.find(id=re.compile(r'boxDetails', re.I))

        logger.debug(f"[PARSE] box_form trouvé: {box_form is not None}")
        logger.debug(f"[PARSE] box_details trouvé: {box_details is not None}")

        # Nom depuis h1
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)
            logger.debug(f"[PARSE] Nom (h1): {detail.name}")

        # Si le nom est le titre du site, on n'est pas sur la bonne page
        if detail.name and "Gestion des prestations" in detail.name:
            logger.error("[PARSE] ❌ Page produit non chargée - session expirée")
            return None

        # ========== CODES ET IDENTIFIANTS ==========
        # Code depuis les liens navigation
        code_match = re.search(r'box_code/([A-Z0-9]+)', html)
        if code_match:
            detail.code = code_match.group(1)
        else:
            code_input = soup.find('input', {'name': re.compile(r'code', re.I)})
            if code_input and code_input.get('value'):
                detail.code = code_input.get('value')
        logger.debug(f"[PARSE] Code: {detail.code}")

        # Collection et Version
        collection_match = re.search(r'boxCollection/([A-Z0-9]+)', html)
        if collection_match:
            detail.collection = collection_match.group(1)

        version_match = re.search(r'boxVersion/([A-Z0-9_]+)', html)
        if version_match:
            detail.version = version_match.group(1)

        # Modèle depuis spans .code (format XX99)
        for span in soup.find_all('span', class_='code'):
            text = span.get_text(strip=True)
            if re.match(r'^[A-Z]{2}\d{2}$', text):
                detail.model = text
                break

        # ========== STATUTS ==========
        # Publisher depuis URL ou selects
        publisher_match = re.search(r'publisher/([A-Z]+)', html)
        if publisher_match:
            detail.publisher = publisher_match.group(1)

        # Chercher les selects pour status et web_status
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', ''))
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '']:
                    if 'status' in name.lower() and 'web' not in name.lower():
                        detail.status = val
                        logger.debug(f"[PARSE] Status: {val}")
                    elif 'webStatus' in name or 'web_status' in name.lower():
                        detail.web_status = val
                        logger.debug(f"[PARSE] Web Status: {val}")
                    elif 'publisher' in name.lower():
                        detail.publisher = val
                        logger.debug(f"[PARSE] Publisher: {val}")

        # ========== PRIX ==========
        # Chercher le prix dans les inputs ou textes
        price_inputs = soup.find_all('input', {'name': re.compile(r'price', re.I)})
        for inp in price_inputs:
            val = inp.get('value', '')
            if val:
                try:
                    detail.price = float(val.replace(',', '.').replace(' ', ''))
                    logger.debug(f"[PARSE] Prix: {detail.price}")
                    break
                except:
                    pass

        # ========== IMAGES ==========
        # Chercher toutes les images du produit
        def normalize_url(url: str) -> str:
            """Normalise l'URL d'une image"""
            if not url:
                return ""
            if url.startswith('//'):
                return f"https:{url}"
            if url.startswith('/'):
                return f"{self.BASE_URL}{url}"
            return url if url.startswith('http') else ""

        # 1. Chercher les inputs/liens contenant des URLs d'images
        for inp in soup.find_all(['input', 'a']):
            val = inp.get('value', '') or inp.get('href', '') or inp.get('data-url', '')
            name = (inp.get('name', '') or inp.get('id', '') or inp.get('class', [''])[0] if isinstance(inp.get('class'), list) else inp.get('class', '')).lower()

            if not val or 'placeholder' in val.lower():
                continue

            val = normalize_url(val)
            if not val:
                continue

            # Classer selon le nom du champ ou du lien
            name_lower = name.lower()
            val_lower = val.lower()

            if 'edito' in name_lower or 'edito' in val_lower:
                if not detail.images.edito:
                    detail.images.edito = val
            elif 'facing' in name_lower or 'facing' in val_lower or '2d' in name_lower:
                if not detail.images.facing_2d:
                    detail.images.facing_2d = val
            elif 'simul' in name_lower or 'simul' in val_lower or '3d' in name_lower:
                if not detail.images.simul_3d:
                    detail.images.simul_3d = val
            elif 'landscape' in name_lower or 'landscape' in val_lower or 'paysage' in name_lower:
                if not detail.images.landscape:
                    detail.images.landscape = val
            elif 'lengow' in name_lower or 'lengow' in val_lower:
                if not detail.images.lengow:
                    detail.images.lengow = val
            elif 'back' in name_lower or 'verso' in name_lower or 'backcard' in val_lower:
                if not detail.images.back_card:
                    detail.images.back_card = val
            elif 'squared' in name_lower or 'squared' in val_lower or 'carre' in name_lower:
                if not detail.images.squared:
                    detail.images.squared = val
            elif 'header' in name_lower or 'header' in val_lower:
                if val not in detail.images.header:
                    detail.images.header.append(val)

        # 2. Chercher dans les balises img
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            alt = img.get('alt', '').lower()
            parent = img.parent
            parent_id = parent.get('id', '').lower() if parent else ''
            parent_class = ' '.join(parent.get('class', [])).lower() if parent else ''

            if not src or 'placeholder' in src.lower() or 'icon' in src.lower():
                continue

            src = normalize_url(src)
            if not src:
                continue

            # Classer selon src, alt, ou contexte parent
            context = f"{src} {alt} {parent_id} {parent_class}".lower()

            if 'edito' in context and not detail.images.edito:
                detail.images.edito = src
            elif ('facing' in context or '2d' in context) and not detail.images.facing_2d:
                detail.images.facing_2d = src
            elif ('simul' in context or '3d' in context) and not detail.images.simul_3d:
                detail.images.simul_3d = src
            elif ('landscape' in context or 'paysage' in context) and not detail.images.landscape:
                detail.images.landscape = src
            elif 'lengow' in context and not detail.images.lengow:
                detail.images.lengow = src
            elif ('back' in context or 'verso' in context) and not detail.images.back_card:
                detail.images.back_card = src
            elif ('squared' in context or 'carre' in context) and not detail.images.squared:
                detail.images.squared = src
            elif 'header' in context and src not in detail.images.header:
                detail.images.header.append(src)

        # 3. Chercher les URLs d'images dans le HTML brut (pattern CDN)
        # Format typique: https://cdn.wonderbox.fr/images/produits/CODE/edito.jpg
        cdn_patterns = [
            (r'https?://[^"\'>\s]+/edito[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'edito'),
            (r'https?://[^"\'>\s]+/facing[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'facing_2d'),
            (r'https?://[^"\'>\s]+/simul[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'simul_3d'),
            (r'https?://[^"\'>\s]+/landscape[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'landscape'),
            (r'https?://[^"\'>\s]+/lengow[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'lengow'),
            (r'https?://[^"\'>\s]+/back[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'back_card'),
            (r'https?://[^"\'>\s]+/squared[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'squared'),
            (r'https?://[^"\'>\s]+/header[^"\'>\s]*\.(jpg|jpeg|png|gif|webp)', 'header'),
        ]

        for pattern, img_type in cdn_patterns:
            matches = re.findall(pattern, html, re.I)
            for match in matches:
                # match est un tuple si le pattern a des groupes
                url = match[0] if isinstance(match, tuple) else match
                if not url.startswith('http'):
                    # Reconstruire l'URL complète
                    full_match = re.search(pattern, html, re.I)
                    if full_match:
                        url = full_match.group(0)

                if img_type == 'header':
                    if url not in detail.images.header:
                        detail.images.header.append(url)
                elif img_type == 'edito' and not detail.images.edito:
                    detail.images.edito = url
                elif img_type == 'facing_2d' and not detail.images.facing_2d:
                    detail.images.facing_2d = url
                elif img_type == 'simul_3d' and not detail.images.simul_3d:
                    detail.images.simul_3d = url
                elif img_type == 'landscape' and not detail.images.landscape:
                    detail.images.landscape = url
                elif img_type == 'lengow' and not detail.images.lengow:
                    detail.images.lengow = url
                elif img_type == 'back_card' and not detail.images.back_card:
                    detail.images.back_card = url
                elif img_type == 'squared' and not detail.images.squared:
                    detail.images.squared = url

        # 4. Chercher les liens vers les images (téléchargement)
        for a in soup.find_all('a', href=re.compile(r'\.(jpg|jpeg|png|gif|webp)', re.I)):
            href = a.get('href', '')
            href = normalize_url(href)
            if not href:
                continue

            link_text = a.get_text(strip=True).lower()
            href_lower = href.lower()

            if ('edito' in link_text or 'edito' in href_lower) and not detail.images.edito:
                detail.images.edito = href
            elif ('facing' in link_text or 'facing' in href_lower) and not detail.images.facing_2d:
                detail.images.facing_2d = href
            elif ('simul' in link_text or 'simul' in href_lower) and not detail.images.simul_3d:
                detail.images.simul_3d = href
            elif ('landscape' in link_text or 'landscape' in href_lower) and not detail.images.landscape:
                detail.images.landscape = href
            elif ('lengow' in link_text or 'lengow' in href_lower) and not detail.images.lengow:
                detail.images.lengow = href
            elif ('back' in link_text or 'back' in href_lower) and not detail.images.back_card:
                detail.images.back_card = href
            elif ('squared' in link_text or 'squared' in href_lower) and not detail.images.squared:
                detail.images.squared = href
            elif 'header' in link_text or 'header' in href_lower:
                if href not in detail.images.header:
                    detail.images.header.append(href)

        logger.debug(f"[PARSE] Images: edito={bool(detail.images.edito)}, facing_2d={bool(detail.images.facing_2d)}, simul_3d={bool(detail.images.simul_3d)}, landscape={bool(detail.images.landscape)}, lengow={bool(detail.images.lengow)}, back_card={bool(detail.images.back_card)}, squared={bool(detail.images.squared)}, header={len(detail.images.header)}")

        # ========== DESCRIPTIONS ==========
        textareas = soup.find_all('textarea')
        logger.debug(f"[PARSE] {len(textareas)} textareas trouvés")

        bullet_points = []
        for ta in textareas:
            ta_id = ta.get('id', ta.get('name', ''))
            content = ta.get_text(strip=True)

            if not content:
                continue

            # Nettoyer HTML
            content_clean = re.sub(r'<[^>]+>', ' ', content)
            content_clean = re.sub(r'\s+', ' ', content_clean).strip()

            # Langue - chercher aussi le format _fr, _en, etc.
            lang_match = re.search(r'[_\-]([a-z]{2})(?:_[A-Z]{2})?$', ta_id)
            lang = lang_match.group(1) if lang_match else 'fr'

            ta_id_lower = ta_id.lower()

            # Mapper les textareas aux descriptions
            if 'targetdescription' in ta_id_lower:
                detail.descriptions.target_description[lang] = content_clean
                if lang == 'fr' and content_clean:
                    bullet_points.append(content_clean)
            elif 'programdescription' in ta_id_lower:
                detail.descriptions.program_description[lang] = content_clean
                if lang == 'fr' and content_clean:
                    bullet_points.append(content_clean)
            elif 'shortdescription' in ta_id_lower:
                detail.descriptions.short_description[lang] = content_clean
            elif 'extradescription' in ta_id_lower or 'fulldescription' in ta_id_lower:
                detail.descriptions.full_description[lang] = content_clean
            elif 'catchphrase' in ta_id_lower:
                detail.descriptions.catch_phrase[lang] = content_clean
            elif 'videolink' in ta_id_lower:
                detail.descriptions.video_link[lang] = content_clean
            elif 'whyyouwillloveit' in ta_id_lower or 'whyyouwilllove' in ta_id_lower:
                detail.descriptions.why_you_will_love[lang] = content_clean
            elif 'presentation_title' in ta_id_lower or 'presentationtitle' in ta_id_lower:
                detail.descriptions.title[lang] = content_clean
                logger.debug(f"[PARSE] Presentation title ({lang}): {content_clean[:50]}...")

        # Chercher aussi dans les inputs pour presentation_title
        for inp in soup.find_all('input'):
            inp_name = inp.get('name', inp.get('id', '')).lower()
            val = inp.get('value', '')
            if val and ('presentation_title' in inp_name or 'presentationtitle' in inp_name):
                lang_match = re.search(r'[_\-]([a-z]{2})(?:_[A-Z]{2})?$', inp_name)
                lang = lang_match.group(1) if lang_match else 'fr'
                if lang not in detail.descriptions.title:
                    detail.descriptions.title[lang] = val
                    logger.debug(f"[PARSE] Presentation title from input ({lang}): {val[:50]}...")

        detail.descriptions.bullet_points = bullet_points[:4]
        logger.debug(f"[PARSE] Descriptions title: {list(detail.descriptions.title.keys())}")

        # ========== MATÉRIALISATIONS ==========
        mat_table = soup.find('table', class_='box-materializations')
        if not mat_table:
            # Essayer d'autres sélecteurs
            mat_table = soup.find('table', class_=re.compile(r'material', re.I))

        if mat_table:
            logger.debug("[PARSE] Table matérialisations trouvée")
            current_mat = None

            for row in mat_table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    first = cells[0].get_text(strip=True)
                    second = cells[1].get_text(strip=True)

                    if first in ['Rematerialisé', 'Dématerialisé', 'Échange', 'Rematérialisé', 'Dématérialisé']:
                        dlu_match = re.search(r'DLU\s*(glissante|fixe)?\s*:?\s*(\d+)\s*mois', second)
                        current_mat = Materialization(
                            type=first,
                            dlu=f"{dlu_match.group(2)} mois" if dlu_match else "",
                            dlu_type=dlu_match.group(1) if dlu_match and dlu_match.group(1) else ""
                        )
                    elif first.lower() == 'available' and current_mat:
                        current_mat.available = second.lower() in ['oui', 'yes', '1', 'true']
                    elif current_mat and re.match(r'^[A-Z]{2}[A-Z0-9]+', first):
                        current_mat.code = first
                        if re.match(r'^\d{13}$', second):
                            current_mat.ean = second
                        detail.materializations.append(current_mat)
                        current_mat = None

        # ========== EAN CODES ==========
        # Extraire tous les codes EAN (13 chiffres)
        ean_pattern = re.compile(r'\b\d{13}\b')
        for span in soup.find_all('span', class_='code'):
            text = span.get_text(strip=True)
            if text and text not in detail.ean_codes:
                detail.ean_codes.append(text)

        # Chercher aussi dans les inputs
        for inp in soup.find_all('input'):
            val = inp.get('value', '')
            name = inp.get('name', '').lower()
            if 'ean' in name and val and re.match(r'^\d{13}$', val):
                if val not in detail.ean_codes:
                    detail.ean_codes.append(val)

        # Chercher dans le HTML brut
        ean_matches = ean_pattern.findall(html)
        for ean in ean_matches[:10]:  # Limiter à 10
            if ean not in detail.ean_codes:
                detail.ean_codes.append(ean)

        logger.debug(f"[PARSE] EAN codes: {detail.ean_codes}")
        logger.debug(f"[PARSE] Matérialisations: {len(detail.materializations)}")

        return detail
    
    def _parse_product_characteristics(self, html: str, detail: ProductDetail):
        """Parse l'onglet Caractéristiques - Extraction MAXIMALE"""
        logger.debug("[PARSE] Parsing Caractéristiques")
        soup = BeautifulSoup(html, 'html.parser')

        # ========== DURÉES ==========
        for cb in soup.find_all('input', {'name': re.compile(r'duration', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                if value and value not in detail.characteristics.durations:
                    detail.characteristics.durations.append(value)
                    logger.debug(f"[PARSE] Durée: {value}")

        # ========== TAGS ==========
        for cb in soup.find_all('input', {'name': re.compile(r'tag', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                label = cb.find_next('label')
                tag_name = label.get_text(strip=True) if label else value
                if tag_name and tag_name not in detail.characteristics.tags:
                    detail.characteristics.tags.append(tag_name)

        # ========== ACTIVITÉS FAVORITES ==========
        # Chercher les checkboxes favoriteActivity, favorite_activity, boxFavoriteActivity, etc.
        favorite_patterns = [
            r'favorite.*activit',
            r'favoriteactivit',
            r'boxfavoriteactivit',
            r'box_favorite_activit',
            r'activit.*favorite',
            r'prestation.*favorite',
            r'favorite.*prestation',
        ]
        for cb in soup.find_all('input', type='checkbox'):
            cb_name = cb.get('name', cb.get('id', '')).lower()

            # Vérifier si le nom correspond à un pattern de favorite activity
            is_favorite = any(re.search(p, cb_name) for p in favorite_patterns)

            if is_favorite and cb.get('checked'):
                value = cb.get('value', '')
                # Chercher le label associé
                label = cb.find_next('label')
                if label:
                    activity_name = label.get_text(strip=True)
                else:
                    # Chercher dans le parent
                    parent = cb.parent
                    if parent:
                        # Enlever le texte de l'input du texte parent
                        activity_name = parent.get_text(strip=True)
                    else:
                        activity_name = value

                if activity_name and activity_name not in detail.characteristics.favorite_activities:
                    detail.characteristics.favorite_activities.append(activity_name)
                    logger.debug(f"[PARSE] Favorite activity: {activity_name}")

        # Chercher aussi dans les selects multi-values
        for select in soup.find_all('select', {'name': re.compile(r'favorite.*activit|activit.*favorite', re.I)}):
            for option in select.find_all('option', selected=True):
                val = option.get_text(strip=True)
                if val and val not in ['--', '', 'Sélectionner'] and val not in detail.characteristics.favorite_activities:
                    detail.characteristics.favorite_activities.append(val)
                    logger.debug(f"[PARSE] Favorite activity (select): {val}")

        logger.debug(f"[PARSE] Total favorite activities: {len(detail.characteristics.favorite_activities)}")

        # ========== WEIGHT (POIDS) ==========
        weight_inputs = soup.find_all('input', {'name': re.compile(r'weight|poids', re.I)})
        for inp in weight_inputs:
            val = inp.get('value', '')
            if val:
                detail.characteristics.weight = val
                logger.debug(f"[PARSE] Poids: {val}")
                break

        # ========== BOOKLET URLS ==========
        for a in soup.find_all('a', href=re.compile(r'booklet|livret|pdf', re.I)):
            href = a.get('href', '')
            text = a.get_text(strip=True).lower()
            if href:
                if href.startswith('/'):
                    href = f"{self.BASE_URL}{href}"
                if 'sans' in text or 'without' in text:
                    detail.characteristics.booklet_url_without_addresses = href
                else:
                    detail.characteristics.booklet_url_with_addresses = href

        # Chercher aussi dans les inputs cachés ou liens
        for inp in soup.find_all('input', {'name': re.compile(r'booklet', re.I)}):
            val = inp.get('value', '')
            if val:
                if 'without' in inp.get('name', '').lower():
                    detail.characteristics.booklet_url_without_addresses = val
                else:
                    detail.characteristics.booklet_url_with_addresses = val

        # ========== META SEO ==========
        for ta in soup.find_all('textarea'):
            ta_id = ta.get('id', ta.get('name', ''))
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

        # ========== SELECTS SUPPLÉMENTAIRES ==========
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', '')).lower()
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '', 'Aucun']:
                    # Log tout select pour debug
                    logger.debug(f"[PARSE] Select {name}: {val}")

        logger.debug(f"[PARSE] Tags: {len(detail.characteristics.tags)}")
        logger.debug(f"[PARSE] Durées: {detail.characteristics.durations}")
        logger.debug(f"[PARSE] Booklets: with={bool(detail.characteristics.booklet_url_with_addresses)}, without={bool(detail.characteristics.booklet_url_without_addresses)}")
    
    def _parse_product_web(self, html: str, detail: ProductDetail):
        """Parse l'onglet Web (Merchandising) - Extraction MAXIMALE"""
        logger.debug("[PARSE] Parsing Web/Merchandising")
        soup = BeautifulSoup(html, 'html.parser')

        # ========== SELECTS ==========
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', ''))
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                selected_value = selected.get('value', '')
                if val and val not in ['--', '', 'Aucun', 'Sélectionner']:
                    name_lower = name.lower()
                    if 'producttype' in name_lower or 'product_type' in name_lower:
                        detail.merchandising.product_type = val
                        logger.debug(f"[PARSE] productType: {val}")
                    elif 'universe' in name_lower or 'univers' in name_lower:
                        detail.merchandising.universe = val
                        logger.debug(f"[PARSE] universe: {val}")
                    elif 'pictogram' in name_lower or 'picto' in name_lower:
                        detail.merchandising.pictogram = val
                        logger.debug(f"[PARSE] pictogram: {val}")

        # ========== THÉMATIQUES ==========
        for cb in soup.find_all('input', {'name': re.compile(r'thematic|thématique', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                # Chercher le label associé
                parent = cb.parent
                label_text = None

                # Chercher label à côté
                label = cb.find_next('label')
                if label:
                    label_text = label.get_text(strip=True)
                elif parent:
                    label_text = parent.get_text(strip=True)

                thematic = label_text or value
                if thematic and thematic not in detail.merchandising.thematics:
                    detail.merchandising.thematics.append(thematic)

        # ========== TYPES DE CIBLES ==========
        for cb in soup.find_all('input', {'name': re.compile(r'targetType|target_type|cible', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                label = cb.find_next('label')
                target = label.get_text(strip=True) if label else value
                if target and target not in detail.merchandising.target_types:
                    detail.merchandising.target_types.append(target)

        # ========== TRANCHES D'ÂGE ==========
        for cb in soup.find_all('input', {'name': re.compile(r'targetAge|target_age|age', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                label = cb.find_next('label')
                age = label.get_text(strip=True) if label else value
                if age and age not in detail.merchandising.target_ages:
                    detail.merchandising.target_ages.append(age)

        # ========== NOMBRE DE PERSONNES ==========
        for cb in soup.find_all('input', {'name': re.compile(r'targetNumber|target_number|nombre|person', re.I)}):
            if cb.get('checked'):
                value = cb.get('value', '')
                label = cb.find_next('label')
                number = label.get_text(strip=True) if label else value
                if number and number not in detail.merchandising.target_numbers:
                    detail.merchandising.target_numbers.append(number)

        # ========== TOUS LES CHECKBOXES COCHÉS (Fallback) ==========
        for cb in soup.find_all('input', type='checkbox', checked=True):
            name = cb.get('name', '').lower()
            value = cb.get('value', '')

            # Skip si déjà traité
            if any(x in name for x in ['thematic', 'targettype', 'targetage', 'targetnumber']):
                continue

            # Extraire le label
            label = cb.find_next('label')
            label_text = label.get_text(strip=True) if label else value

            # Classer selon le nom du champ
            if 'boxthematic' in name and label_text not in detail.merchandising.thematics:
                detail.merchandising.thematics.append(label_text)
            elif 'targettype' in name and label_text not in detail.merchandising.target_types:
                detail.merchandising.target_types.append(label_text)
            elif 'targetage' in name and label_text not in detail.merchandising.target_ages:
                detail.merchandising.target_ages.append(label_text)
            elif 'targetnumber' in name and label_text not in detail.merchandising.target_numbers:
                detail.merchandising.target_numbers.append(label_text)

        logger.debug(f"[PARSE] Thematics: {detail.merchandising.thematics}")
        logger.debug(f"[PARSE] Target types: {detail.merchandising.target_types}")
        logger.debug(f"[PARSE] Target ages: {detail.merchandising.target_ages}")
        logger.debug(f"[PARSE] Target numbers: {detail.merchandising.target_numbers}")
    
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
        """Parse une ligne activité - Extraction MAXIMALE"""
        cells = row.find_all('td')
        if len(cells) < 7:
            return None

        activity = Activity()

        # ========== STATUT DEPUIS CLASSE ==========
        row_classes = row.get('class', [])
        for cls in row_classes:
            if cls not in ['bg-light', 'bg-dark']:
                activity.status = cls
                # Interpréter les classes courantes
                cls_lower = cls.lower()
                if 'active' in cls_lower and 'publish' in cls_lower:
                    activity.web_status = 'ACTIVE'
                elif 'active' in cls_lower:
                    activity.status = 'active'
                elif 'archived' in cls_lower:
                    activity.status = 'archived'
                    activity.web_status = 'ARCHIVED'
                elif 'pending' in cls_lower:
                    activity.status = 'pending'
                break

        # ========== CODE ET ID ==========
        if len(cells) > 2:
            code_link = cells[2].find('a', href=re.compile(r'/activity/index/id/'))
            if code_link:
                activity.code = code_link.get_text(strip=True)
                href = code_link.get('href', '')
                match = re.search(r'/id/(\d+)', href)
                if match:
                    activity.id = int(match.group(1))
                    activity.detail_url = f"{self.BASE_URL}/activity/index/id/{activity.id}"

        # ========== STATUT TEXTUEL (cellule 3 souvent) ==========
        if len(cells) > 3:
            status_text = cells[3].get_text(strip=True)
            if status_text and status_text not in ['-', '']:
                if not activity.status:
                    activity.status = status_text

        # ========== WEB STATUS (cellule 4 souvent) ==========
        if len(cells) > 4:
            web_status_text = cells[4].get_text(strip=True)
            if web_status_text and web_status_text not in ['-', '']:
                activity.web_status = web_status_text

        # ========== NOM, TYPE, CIBLE ==========
        if len(cells) > 5:
            name_link = cells[5].find('a', href=re.compile(r'/activity/index/id/'))
            if name_link:
                activity.name = name_link.get_text(strip=True)

            parts = cells[5].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                activity.activity_type = parts[1].strip()
            if len(parts) >= 3:
                # Peut contenir le sous-type
                activity.activity_subtype = parts[2].strip() if parts[2].strip() not in ['-', ''] else ""
            if len(parts) >= 4:
                activity.target = parts[3].strip()

        # ========== LOCATION COMPLÈTE ==========
        if len(cells) > 6:
            loc_link = cells[6].find('a', href=re.compile(r'/location/index/id/'))
            if loc_link:
                activity.location_name = loc_link.get_text(strip=True)
                # Extraire l'ID du lieu
                loc_href = loc_link.get('href', '')
                loc_id_match = re.search(r'/id/(\d+)', loc_href)
                if loc_id_match:
                    activity.location_id = int(loc_id_match.group(1))

            parts = cells[6].get_text(separator='|', strip=True).split('|')
            if len(parts) >= 2:
                activity.location_address = parts[1].strip()
            if len(parts) >= 3:
                activity.location_zipcode = parts[2].strip()
            if len(parts) >= 4:
                activity.location_city = parts[3].strip()
            if len(parts) >= 5:
                activity.location_country = parts[4].strip()
            if len(parts) >= 6:
                # Peut contenir code lieu ou région
                extra = parts[5].strip()
                if re.match(r'^[A-Z]{2}\d+', extra):
                    activity.location_code = extra
                else:
                    activity.location_region = extra

        # ========== PARTENAIRE (cellule supplémentaire parfois) ==========
        for i, cell in enumerate(cells):
            cell_html = str(cell)
            if '/partner/index/id/' in cell_html:
                partner_link = cell.find('a', href=re.compile(r'/partner/index/id/'))
                if partner_link:
                    activity.partner_name = partner_link.get_text(strip=True)
                break

        # ========== DURÉE / POIDS (colonnes supplémentaires) ==========
        for cell in cells:
            cell_text = cell.get_text(strip=True).lower()
            # Durée (ex: "2h", "30min", "1 jour")
            duration_match = re.search(r'(\d+)\s*(h|min|jour|day|nuit|night)', cell_text)
            if duration_match and not activity.duration:
                activity.duration = f"{duration_match.group(1)}{duration_match.group(2)}"

            # Nombre de personnes
            persons_match = re.search(r'(\d+)\s*(pers|person|pax)', cell_text)
            if persons_match and not activity.nb_persons:
                activity.nb_persons = persons_match.group(1)

        # ========== PRIX ==========
        if len(cells) > 7:
            price_text = cells[7].get_text(strip=True)
            match = re.search(r'([\d\s,\.]+)\s*€', price_text)
            if match:
                try:
                    activity.price = float(match.group(1).replace(' ', '').replace(',', '.'))
                except:
                    pass

            # Pays
            country_match = re.search(r'\(([^)]+)\)', price_text)
            if country_match:
                activity.price_countries = country_match.group(1).strip()

        # ========== PRIX PARTENAIRE / MARGE (colonnes supplémentaires) ==========
        for cell in cells[-3:]:  # Vérifier les dernières colonnes
            cell_text = cell.get_text(strip=True)
            # Prix partenaire
            if 'partenaire' in str(cell).lower() or 'partner' in str(cell).lower():
                partner_price_match = re.search(r'([\d\s,\.]+)\s*€', cell_text)
                if partner_price_match:
                    try:
                        activity.partner_price = float(partner_price_match.group(1).replace(' ', '').replace(',', '.'))
                    except:
                        pass

            # Marge
            margin_match = re.search(r'([\d,\.]+)\s*%', cell_text)
            if margin_match:
                try:
                    activity.margin_rate = float(margin_match.group(1).replace(',', '.'))
                except:
                    pass

        # ========== PUBLISHER (colonne supplémentaire) ==========
        for cell in cells:
            cell_text = cell.get_text(strip=True).upper()
            if cell_text in ['FRANCE', 'BELGIUM', 'SPAIN', 'ITALY', 'PORTUGAL', 'NETHERLANDS']:
                activity.publisher = cell_text
                break

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
        """Parse l'onglet Présentation d'une activité - Extraction MAXIMALE"""
        logger.debug("[PARSE] Parsing Présentation activité")
        soup = BeautifulSoup(html, 'html.parser')

        detail = ActivityDetail(id=activity_id)
        detail.detail_url = f"{self.BASE_URL}/activity/index/id/{activity_id}"

        # ========== NOM ==========
        h1 = soup.find('h1')
        if h1:
            raw_name = h1.get_text(strip=True)
            detail.name = re.sub(r'^[^\w]*', '', raw_name)
            logger.debug(f"[PARSE] Nom: {detail.name}")

        # ========== CODE ==========
        for a in soup.find_all('a', href=re.compile(r'/activity/index/id/')):
            text = a.get_text(strip=True)
            if re.match(r'^[A-Z0-9]{5,}$', text):
                detail.code = text
                break

        if not detail.code:
            code_match = re.search(r'>([A-Z][A-Z0-9]{5,})</a>', html)
            if code_match:
                detail.code = code_match.group(1)

        # Aussi chercher dans les inputs
        code_input = soup.find('input', {'name': re.compile(r'code', re.I)})
        if code_input and code_input.get('value') and not detail.code:
            detail.code = code_input.get('value')

        logger.debug(f"[PARSE] Code: {detail.code}")

        # ========== STATUTS ==========
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', '')).lower()
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                if val and val not in ['--', '', 'Aucun']:
                    if 'status' in name and 'web' not in name:
                        detail.status = val
                        logger.debug(f"[PARSE] Status: {val}")
                    elif 'webstatus' in name or 'web_status' in name:
                        detail.web_status = val
                        logger.debug(f"[PARSE] Web Status: {val}")
                    elif 'publisher' in name:
                        detail.publisher = val
                        logger.debug(f"[PARSE] Publisher: {val}")
                    elif 'target' in name:
                        detail.target = val
                        logger.debug(f"[PARSE] Target: {val}")

        # ========== LOCATION COMPLÈTE ==========
        loc_link = soup.find('a', href=re.compile(r'/location/index/id/'))
        if loc_link:
            detail.location.name = loc_link.get_text(strip=True)
            match = re.search(r'/id/(\d+)', loc_link.get('href', ''))
            if match:
                detail.location.id = int(match.group(1))

        # Extraire adresse depuis les inputs ou textes
        for inp in soup.find_all('input'):
            name = inp.get('name', '').lower()
            value = inp.get('value', '')
            if not value:
                continue

            if 'address' in name or 'adresse' in name:
                detail.location.address = value
            elif 'zipcode' in name or 'postal' in name or 'cp' in name:
                detail.location.zipcode = value
            elif 'city' in name or 'ville' in name:
                detail.location.city = value
            elif 'country' in name or 'pays' in name:
                detail.location.country = value
            elif 'phone' in name or 'tel' in name:
                detail.location.phone = value
            elif 'email' in name:
                detail.location.email = value
            elif 'website' in name or 'url' in name:
                detail.location.website = value
            elif 'lat' in name:
                detail.location.latitude = value
            elif 'lon' in name or 'lng' in name:
                detail.location.longitude = value
            elif 'region' in name:
                detail.location.region = value
            elif 'department' in name:
                detail.location.department = value

        # Chercher aussi dans les selects pour pays
        for select in soup.find_all('select', {'name': re.compile(r'country|pays', re.I)}):
            selected = select.find('option', selected=True)
            if selected:
                detail.location.country = selected.get_text(strip=True)

        logger.debug(f"[PARSE] Location: {detail.location.name}, {detail.location.city}, {detail.location.country}")

        # ========== PARTENAIRE ==========
        partner_link = soup.find('a', href=re.compile(r'/partner/index/id/'))
        if partner_link:
            detail.partner_name = partner_link.get_text(strip=True)
            # Extraire le code partenaire si présent
            partner_code_match = re.search(r'>([A-Z0-9]+)</a>', str(partner_link))
            if partner_code_match:
                potential_code = partner_code_match.group(1)
                if re.match(r'^[A-Z0-9]{3,}$', potential_code):
                    detail.partner_code = potential_code

        # ========== DESCRIPTIONS ==========
        for ta in soup.find_all('textarea'):
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

            ta_id_lower = ta_id.lower()
            if 'name' in ta_id_lower or 'nom' in ta_id_lower:
                detail.descriptions.name[lang] = content_clean
            elif 'description' in ta_id_lower and 'short' not in ta_id_lower:
                detail.descriptions.description[lang] = content_clean
            elif 'short' in ta_id_lower:
                detail.descriptions.short_description[lang] = content_clean
            elif 'condition' in ta_id_lower:
                detail.descriptions.conditions[lang] = content_clean
            elif 'practical' in ta_id_lower or 'pratique' in ta_id_lower:
                detail.descriptions.practical_info[lang] = content_clean
            elif 'includ' in ta_id_lower or 'compris' in ta_id_lower:
                if 'not' in ta_id_lower or 'non' in ta_id_lower:
                    detail.descriptions.not_included[lang] = content_clean
                else:
                    detail.descriptions.included[lang] = content_clean
            elif 'highlight' in ta_id_lower or 'point' in ta_id_lower:
                detail.descriptions.highlights[lang] = content_clean

        # ========== IMAGES ==========
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and 'placeholder' not in src.lower():
                if src.startswith('/'):
                    src = f"{self.BASE_URL}{src}"
                if src.startswith('http') and src not in detail.images:
                    detail.images.append(src)

        # ========== PRODUITS ASSOCIÉS ==========
        for a in soup.find_all('a', href=re.compile(r'/box/index/id/')):
            text = a.get_text(strip=True)
            if re.match(r'^[A-Z0-9]{6,}$', text):  # Code coffret
                if text not in detail.products:
                    detail.products.append(text)

        logger.debug(f"[PARSE] Images: {len(detail.images)}")
        logger.debug(f"[PARSE] Produits associés: {detail.products}")

        return detail
    
    def _parse_activity_characteristics(self, html: str, detail: ActivityDetail):
        """Parse l'onglet Caractéristiques d'une activité - Extraction MAXIMALE"""
        logger.debug("[PARSE] Parsing Caractéristiques activité")
        soup = BeautifulSoup(html, 'html.parser')

        # ========== SELECTS ==========
        for select in soup.find_all('select'):
            name = select.get('name', select.get('id', '')).lower()
            selected = select.find('option', selected=True)
            if selected:
                val = selected.get_text(strip=True)
                selected_value = selected.get('value', '')
                if val and val not in ['--', '', 'Aucun', 'Sélectionner']:
                    if 'duration' in name:
                        detail.characteristics.duration = val
                        logger.debug(f"[PARSE] Duration: {val}")
                    elif 'roomtype' in name or 'room_type' in name:
                        detail.characteristics.room_type = val
                        logger.debug(f"[PARSE] Room Type: {val}")
                    elif 'activitytype' in name or 'activity_type' in name:
                        detail.characteristics.activity_type = val
                        logger.debug(f"[PARSE] Activity Type: {val}")
                    elif 'subtype' in name:
                        detail.characteristics.activity_subtype = val
                    elif 'daymoment' in name or 'day_moment' in name:
                        detail.characteristics.day_moment = val
                    elif 'mealmoment' in name or 'meal_moment' in name:
                        detail.characteristics.meal_moment = val
                    elif 'family' in name or 'famille' in name:
                        detail.characteristics.family = val
                    elif 'edition' in name:
                        detail.characteristics.edition = val
                    elif 'promo' in name:
                        detail.characteristics.promo_action = val
                    elif 'person' in name or 'nb' in name:
                        detail.characteristics.nb_persons = val
                    elif 'validity' in name or 'validite' in name:
                        detail.characteristics.validity_days = val
                    elif 'booking' in name or 'delay' in name or 'delai' in name:
                        detail.characteristics.booking_delay = val
                    elif 'cancel' in name or 'annulation' in name:
                        detail.characteristics.cancellation_policy = val

        # ========== INPUTS ==========
        for inp in soup.find_all('input'):
            input_type = inp.get('type', 'text').lower()
            name = inp.get('name', inp.get('id', '')).lower()
            value = inp.get('value', '')

            if input_type == 'text' and value:
                if 'weight' in name or 'poids' in name:
                    detail.characteristics.weight = value
                    logger.debug(f"[PARSE] Weight: {value}")
                elif 'capacity' in name and 'min' in name:
                    try:
                        detail.characteristics.capacity_min = int(value)
                    except:
                        pass
                elif 'capacity' in name and 'max' in name:
                    try:
                        detail.characteristics.capacity_max = int(value)
                    except:
                        pass
                elif 'person' in name or 'nb' in name:
                    detail.characteristics.nb_persons = value

        # ========== CHECKBOXES ==========
        for cb in soup.find_all('input', type='checkbox'):
            name = cb.get('name', '').lower()
            value = cb.get('value', '')
            is_checked = cb.get('checked') is not None

            # Extraire le label
            label = cb.find_next('label')
            label_text = label.get_text(strip=True) if label else value

            if is_checked:
                if 'agebracket' in name or 'age_bracket' in name or 'age' in name:
                    if label_text and label_text not in detail.characteristics.age_brackets:
                        detail.characteristics.age_brackets.append(label_text)
                elif 'hotelservice' in name or 'hotel_service' in name:
                    detail.characteristics.hotel_service = True
                elif 'manualcheck' in name or 'manual_check' in name:
                    detail.characteristics.manual_check_allowed = True
                elif 'reservation' in name:
                    detail.characteristics.reservation_required = True
                elif 'season' in name or 'saison' in name:
                    if label_text and label_text not in detail.characteristics.seasons:
                        detail.characteristics.seasons.append(label_text)
                elif 'day' in name and 'available' in name:
                    if label_text and label_text not in detail.characteristics.days_available:
                        detail.characteristics.days_available.append(label_text)
                elif 'language' in name or 'langue' in name:
                    if label_text and label_text not in detail.characteristics.languages:
                        detail.characteristics.languages.append(label_text)
                elif 'access' in name:
                    if label_text and label_text not in detail.characteristics.accessibility:
                        detail.characteristics.accessibility.append(label_text)
                elif 'equipment' in name and 'provid' in name:
                    if label_text and label_text not in detail.characteristics.equipment_provided:
                        detail.characteristics.equipment_provided.append(label_text)
                elif 'equipment' in name and 'requir' in name:
                    if label_text and label_text not in detail.characteristics.equipment_required:
                        detail.characteristics.equipment_required.append(label_text)

        # ========== PRICING ==========
        for inp in soup.find_all('input'):
            name = inp.get('name', '').lower()
            value = inp.get('value', '')

            if not value:
                continue

            try:
                float_val = float(value.replace(',', '.').replace(' ', ''))
                if 'saler' in name:
                    detail.pricing.salers = value
                elif 'value' in name and 'price' not in name:
                    detail.pricing.value = float_val
                elif 'reimbursement' in name or 'remboursement' in name:
                    detail.pricing.reimbursement = float_val
                elif 'margin' in name or 'marge' in name:
                    detail.pricing.margin_rate = float_val
                elif 'commission' in name:
                    if 'rate' in name or 'taux' in name:
                        detail.pricing.commission_rate = float_val
                    else:
                        detail.pricing.commission = float_val
                elif 'partner' in name and 'price' in name:
                    detail.pricing.partner_price = float_val
                elif 'public' in name and 'price' in name:
                    detail.pricing.public_price = float_val
            except:
                pass

        logger.debug(f"[PARSE] Age brackets: {detail.characteristics.age_brackets}")
        logger.debug(f"[PARSE] Duration: {detail.characteristics.duration}")
        logger.debug(f"[PARSE] Weight: {detail.characteristics.weight}")
        logger.debug(f"[PARSE] Seasons: {detail.characteristics.seasons}")
        logger.debug(f"[PARSE] Pricing value: {detail.pricing.value}")
    
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

    # ========================================================================
    # RECHERCHE PAR PAYS / LOCALISATION
    # ========================================================================

    def search_activities_by_country(self, country: str, publisher: str = "FRANCE",
                                     web_status: str = "ACTIVE", page: int = 1) -> Tuple[List[Activity], int, int]:
        """Recherche les activités par pays de localisation"""
        self._log_separator(f"RECHERCHE ACTIVITÉS PAR PAYS - {country} - Page {page}")

        # Construire l'URL avec le filtre pays
        url_parts = [
            f"{self.BASE_URL}/search/activity",
            f"location_country/{country}"
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

        html = self._fetch_page("/".join(url_parts), f"Activités pays {country} page {page}")
        if not html:
            return [], 0, 0

        return self._parse_activities_results(html)

    def get_all_activities_by_country(self, country: str, publisher: str = "FRANCE",
                                      web_status: str = "ACTIVE", max_pages: int = None,
                                      progress_callback=None) -> List[Activity]:
        """Récupère toutes les activités d'un pays"""
        all_activities = []
        activities, total, total_pages = self.search_activities_by_country(country, publisher, web_status, 1)
        all_activities.extend(activities)

        if progress_callback:
            progress_callback(1, total_pages, len(all_activities), total)

        if max_pages:
            total_pages = min(total_pages, max_pages)

        for page in range(2, total_pages + 1):
            activities, _, _ = self.search_activities_by_country(country, publisher, web_status, page)
            all_activities.extend(activities)
            if progress_callback:
                progress_callback(page, total_pages, len(all_activities), total)
            time.sleep(0.3)

        return all_activities

    def search_products_by_country(self, country: str, publisher: str = "FRANCE",
                                   web_status: str = "ACTIVE", page: int = 1) -> Tuple[List[Product], int, int]:
        """Recherche les produits par pays"""
        self._log_separator(f"RECHERCHE PRODUITS PAR PAYS - {country} - Page {page}")

        # Construire l'URL avec le filtre pays
        url_parts = [f"{self.BASE_URL}/search/box"]
        if publisher:
            url_parts.append(f"publisher/{publisher}")
        if web_status:
            url_parts.append(f"boxPublishStatus_webStatus/{web_status}")
        # Ajouter filtre pays (selon l'API du site)
        url_parts.append(f"country/{country}")
        url_parts.extend([
            "boxedShops_nullable/0",
            "in_boxedChecks_check_commissionFree/0",
            "notIn_boxedChecks_check_commissionFree/0",
            f"page/{page}"
        ])

        html = self._fetch_page("/".join(url_parts), f"Produits pays {country} page {page}")
        if not html:
            return [], 0, 0

        return self._parse_search_results(html)

    def get_all_products_by_country(self, country: str, publisher: str = "FRANCE",
                                    web_status: str = "ACTIVE", max_pages: int = None,
                                    include_details: bool = False,
                                    progress_callback=None) -> List[Product]:
        """Récupère tous les produits d'un pays avec optionnellement leurs détails"""
        all_products = []
        products, total, total_pages = self.search_products_by_country(country, publisher, web_status, 1)
        all_products.extend(products)

        if progress_callback:
            progress_callback(1, total_pages, len(all_products), total)

        if max_pages:
            total_pages = min(total_pages, max_pages)

        for page in range(2, total_pages + 1):
            products, _, _ = self.search_products_by_country(country, publisher, web_status, page)
            all_products.extend(products)
            if progress_callback:
                progress_callback(page, total_pages, len(all_products), total)
            time.sleep(0.3)

        # Charger les détails si demandé
        if include_details:
            logger.info(f"Chargement des détails pour {len(all_products)} produits...")
            for i, product in enumerate(all_products):
                if product.id:
                    if progress_callback:
                        progress_callback(i + 1, len(all_products), product.code, "détails")
                    product.details = self.get_product_detail(product.id)
                    time.sleep(0.2)

        return all_products

    def get_available_countries(self) -> List[str]:
        """Retourne la liste des pays disponibles"""
        return [
            "FR",  # France
            "BE",  # Belgique
            "ES",  # Espagne
            "IT",  # Italie
            "PT",  # Portugal
            "NL",  # Pays-Bas
            "CH",  # Suisse
            "LU",  # Luxembourg
            "MC",  # Monaco
            "AD",  # Andorre
        ]

    def get_statistics(self, products: List[Product]) -> dict:
        """Calcule des statistiques sur une liste de produits"""
        stats = {
            "total_products": len(products),
            "products_with_details": sum(1 for p in products if p.details),
            "products_with_activities": sum(1 for p in products if p.activities),
            "total_activities": sum(len(p.activities or []) for p in products),
            "prices": {},
            "by_publisher": {},
            "by_status": {},
            "by_universe": {},
            "by_product_type": {},
        }

        # Prix
        prices = [p.price for p in products if p.price]
        if prices:
            stats["prices"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "count": len(prices)
            }

        # Par éditeur
        for p in products:
            pub = p.publisher or "Unknown"
            stats["by_publisher"][pub] = stats["by_publisher"].get(pub, 0) + 1

        # Par statut
        for p in products:
            status = p.status or p.web_status or "Unknown"
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # Par univers (si détails disponibles)
        for p in products:
            if p.details and p.details.merchandising.universe:
                universe = p.details.merchandising.universe
                stats["by_universe"][universe] = stats["by_universe"].get(universe, 0) + 1

        # Par type
        for p in products:
            ptype = p.product_type or "Unknown"
            stats["by_product_type"][ptype] = stats["by_product_type"].get(ptype, 0) + 1

        return stats
