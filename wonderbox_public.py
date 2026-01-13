"""
Wonderbox Public API Scraper
============================
Scraping du site public wonderbox.fr via les APIs webservices
"""

import requests
import logging
import re
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from bs4 import BeautifulSoup

logger = logging.getLogger("WonderboxPublic")


# ============================================================================
# MODÈLES DE DONNÉES - API PUBLIQUE
# ============================================================================

@dataclass
class PublicProduct:
    """Produit depuis l'API publique wonderbox.fr"""
    code: str = ""
    name: str = ""
    url: str = ""
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[int] = None
    currency: str = "EUR"
    # Images
    image_url: str = ""
    images: List[Dict[str, str]] = field(default_factory=list)
    # Compteurs
    activity_count: int = 0
    average_rating: Optional[float] = None
    review_count: int = 0
    bookable_online: bool = False
    # Catégories
    categories: List[str] = field(default_factory=list)
    category_codes: List[str] = field(default_factory=list)
    # Descriptions
    description: str = ""
    short_description: str = ""
    summary: str = ""
    # Caractéristiques
    duration: str = ""
    validity: str = ""
    universe: str = ""
    thematics: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    # SEO
    meta_title: str = ""
    meta_description: str = ""
    # Données brutes
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PartnerReview:
    """Avis client d'un partenaire"""
    id: str = ""  # contentId (ex: 147667412)
    title: str = ""  # Titre de l'avis
    comment: str = ""  # Contenu de l'avis
    rating: int = 0  # Note (1-5 étoiles)
    username: str = ""  # Nom de l'utilisateur
    date: str = ""  # Date de l'avis (ex: 28/07/2022)
    experience_date: str = ""  # Mois de l'expérience (ex: juillet 2022)
    activity_code: str = ""  # Code activité liée (ex: AJGA31)
    activity_name: str = ""  # Nom de l'activité
    helpful_count: int = 0  # Nombre de personnes ayant trouvé l'avis utile


@dataclass
class PartnerActivity:
    """Activité extraite de la page partenaire (via data-gtm-box)"""
    id: str = ""  # Code activité (ex: ALCMB1)
    name: str = ""  # Slug name (ex: un_acces_au_hammam_en_duo...)
    theme: str = ""  # Ex: Spa & thalasso
    subtheme: str = ""  # Ex: Hammam
    category: str = ""  # dimension11 (ex: beauté & bien-être)
    price: Optional[float] = None
    price_discount: Optional[float] = None
    department: str = ""  # dimension13 (ex: de27)
    type: str = ""  # dimension12 (ex: classic)


@dataclass
class PublicPartner:
    """Partenaire depuis le site wonderbox.fr (via HTML)"""
    code: str = ""  # Code partenaire (ex: LL0W21)
    name: str = ""  # Nom du partenaire
    slug: str = ""  # Slug URL (ex: antik-spa-le-neubourg)
    url: str = ""  # URL complète
    theme: str = ""  # Ex: relaxation
    subtheme: str = ""  # Ex: Hammam
    category: str = ""  # dimension11 (ex: relaxation)
    # Localisation
    address: str = ""
    city: str = ""
    zipcode: str = ""
    region: str = ""
    department: str = ""
    country: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Contact
    phone: str = ""
    email: str = ""
    website: str = ""
    # Contenu
    description: str = ""
    highlights: List[str] = field(default_factory=list)
    included: List[str] = field(default_factory=list)
    practical_info: str = ""
    # Images
    images: List[str] = field(default_factory=list)
    # Avis
    average_rating: Optional[float] = None
    review_count: int = 0
    rating_distribution: Dict[int, int] = field(default_factory=dict)  # {5: 91, 4: 5, 3: 0, 2: 0, 1: 5} en pourcentage
    reviews: List[PartnerReview] = field(default_factory=list)  # Liste des avis
    # Produits associés (codes coffrets)
    products: List[str] = field(default_factory=list)
    # Activités du partenaire
    activities: List[PartnerActivity] = field(default_factory=list)
    # Données brutes
    raw_html: str = ""


@dataclass
class PublicActivity:
    """Activité depuis l'API publique wonderbox.fr"""
    id: str = ""  # Code activité (ex: ANZCB1)
    name: str = ""
    partner_name: str = ""
    partner_code: str = ""  # Code partenaire (ex: LL0W21)
    partner_url: str = ""  # URL complète du partenaire
    city: str = ""
    region: str = ""
    country: str = ""
    address: str = ""
    zipcode: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    average_rating: Optional[float] = None
    review_count: int = 0
    image_url: str = ""
    description: str = ""
    theme: str = ""  # Ex: relaxation
    # Données brutes
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategorySearchResult:
    """Résultat de recherche par catégorie"""
    category_code: str = ""
    total_products: int = 0
    current_page: int = 0
    page_size: int = 16
    next_page_url: str = ""
    products: List[PublicProduct] = field(default_factory=list)
    facets: List[Dict] = field(default_factory=list)
    selected_filters: List[Dict] = field(default_factory=list)


@dataclass
class ProductActivitiesResult:
    """Résultat des activités d'un produit"""
    product_code: str = ""
    total_activities: int = 0
    current_page: int = 0
    page_size: int = 8
    activities: List[PublicActivity] = field(default_factory=list)
    facets: List[Dict] = field(default_factory=list)


# ============================================================================
# SCRAPER API PUBLIQUE
# ============================================================================

class WonderboxPublicScraper:
    """Scraper pour l'API publique de wonderbox.fr"""

    BASE_URL = "https://www.wonderbox.fr/wonderpublicwebservices/v2/wonderbox-fr/fr"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        })

    def _log_separator(self, title: str):
        logger.info(f"{'='*20} {title} {'='*20}")

    def _fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Récupère du JSON depuis l'API"""
        try:
            logger.debug(f"[FETCH] GET {url}")
            if params:
                logger.debug(f"[FETCH] Params: {params}")

            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()

            data = resp.json()
            logger.debug(f"[FETCH] ✅ {len(str(data))} chars")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"[FETCH] ❌ Erreur: {e}")
            return None
        except ValueError as e:
            logger.error(f"[FETCH] ❌ JSON invalide: {e}")
            return None

    # ========================================================================
    # RECHERCHE PAR CATÉGORIE
    # ========================================================================

    def search_category(
        self,
        category_code: str,
        filters: str = "",
        page: int = 1,
        page_size: int = 16
    ) -> Optional[CategorySearchResult]:
        """
        Recherche des produits dans une catégorie

        Args:
            category_code: Code de la catégorie (ex: "233388", "155661")
            filters: Filtres optionnels (ex: "NW-6485-localisation~centre")
            page: Numéro de page (1-indexed)
            page_size: Nombre de produits par page

        Returns:
            CategorySearchResult ou None si erreur
        """
        self._log_separator(f"SEARCH CATEGORY {category_code}")

        # Construction de la query
        query = f"/c/{category_code}"
        if filters:
            query += f"/{filters}"
        if page > 1:
            query += f"/I-Page{page}_{page_size}"

        url = f"{self.BASE_URL}/products/search"
        data = self._fetch_json(url, params={"query": query})

        if not data:
            return None

        result = CategorySearchResult(
            category_code=data.get("categoryCode", category_code),
            current_page=data.get("pagination", {}).get("currentPage", 0),
            page_size=data.get("pagination", {}).get("pageSize", page_size),
            next_page_url=data.get("pagination", {}).get("nextPageUrl", ""),
            facets=data.get("facets", []),
            selected_filters=data.get("selectedFilters", []),
        )

        # Parser les produits
        for p in data.get("products", []):
            product = self._parse_product(p)
            result.products.append(product)

        result.total_products = data.get("pagination", {}).get("totalResults", len(result.products))

        logger.info(f"✅ {len(result.products)} produits trouvés (page {result.current_page + 1})")
        return result

    def search_category_all_pages(
        self,
        category_code: str,
        filters: str = "",
        max_pages: int = None,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> List[PublicProduct]:
        """
        Récupère tous les produits d'une catégorie (toutes les pages)

        Args:
            category_code: Code de la catégorie
            filters: Filtres optionnels
            max_pages: Nombre max de pages (None = toutes)
            progress_callback: Callback(current_page, total_pages, last_code)

        Returns:
            Liste de tous les produits
        """
        self._log_separator(f"SEARCH ALL PAGES {category_code}")

        all_products = []
        page = 1
        total_pages = None

        while True:
            result = self.search_category(category_code, filters, page)

            if not result or not result.products:
                break

            all_products.extend(result.products)

            # Calculer total pages
            if total_pages is None and result.total_products:
                total_pages = (result.total_products + result.page_size - 1) // result.page_size

            if progress_callback:
                progress_callback(page, total_pages or page, result.products[-1].code if result.products else "")

            # Vérifier si on continue
            if not result.next_page_url:
                break
            if max_pages and page >= max_pages:
                break

            page += 1

        logger.info(f"✅ Total: {len(all_products)} produits en {page} pages")
        return all_products

    def _parse_product(self, data: Dict) -> PublicProduct:
        """Parse un produit depuis la réponse API"""
        product = PublicProduct(
            code=data.get("code", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            bookable_online=data.get("bookableOnline", False),
            activity_count=int(data.get("activityCount", 0) or 0),
            average_rating=data.get("averageRating"),
            review_count=int(data.get("reviewCount", 0) or 0),
            raw_data=data,
        )

        # Prix
        price_data = data.get("price", {})
        if price_data:
            product.price = price_data.get("value")
            product.currency = price_data.get("currencyIso", "EUR")

        # Prix original (si promo)
        original_price = data.get("originalPrice", {})
        if original_price:
            product.original_price = original_price.get("value")

        product.discount_percentage = data.get("discountPercentage")

        # Images - toutes les images disponibles
        images = data.get("images", [])
        if images:
            product.image_url = images[0].get("url", "")
            product.images = [
                {"url": img.get("url", ""), "format": img.get("format", ""), "type": img.get("imageType", "")}
                for img in images
            ]

        # Catégories
        categories = data.get("categories", [])
        product.categories = [c.get("name", "") for c in categories if c.get("name")]
        product.category_codes = [c.get("code", "") for c in categories if c.get("code")]

        # Descriptions
        product.description = data.get("description", "")
        product.short_description = data.get("shortDescription", "")
        product.summary = data.get("summary", "")

        # Caractéristiques
        product.duration = data.get("duration", "")
        product.validity = data.get("validity", "")
        product.universe = data.get("universe", "")

        # Thématiques
        thematics = data.get("thematics", [])
        if thematics:
            product.thematics = [t.get("name", "") for t in thematics if t.get("name")]

        # Points forts / highlights
        highlights = data.get("highlights", [])
        if highlights:
            product.highlights = highlights if isinstance(highlights, list) else []

        # SEO
        product.meta_title = data.get("metaTitle", "")
        product.meta_description = data.get("metaDescription", "")

        return product

    # ========================================================================
    # ACTIVITÉS D'UN PRODUIT
    # ========================================================================

    def get_product_activities(
        self,
        product_code: str,
        filters: str = "",
        page: int = 1,
        page_size: int = 8
    ) -> Optional[ProductActivitiesResult]:
        """
        Récupère les activités d'un produit

        Args:
            product_code: Code du produit (ex: "B33O01")
            filters: Filtres optionnels (ex: "parentRegion~ile-de-france")
            page: Numéro de page
            page_size: Nombre d'activités par page

        Returns:
            ProductActivitiesResult ou None si erreur
        """
        self._log_separator(f"PRODUCT ACTIVITIES {product_code}")

        # Construction du urlPath
        url_path = f"/b/{product_code}"
        if filters:
            url_path += f"/{filters}"
        if page > 1:
            url_path += f"/I-Page{page}_{page_size}"

        url = f"{self.BASE_URL}/filters/activities/{product_code}"
        data = self._fetch_json(url, params={"urlPath": url_path})

        if not data:
            return None

        result = ProductActivitiesResult(
            product_code=data.get("code", product_code),
            current_page=data.get("pagination", {}).get("currentPage", 0),
            page_size=data.get("pagination", {}).get("pageSize", page_size),
            facets=data.get("facets", []),
        )

        # Parser les activités (sparkowActivities)
        for a in data.get("sparkowActivities", []):
            activity = self._parse_activity(a)
            result.activities.append(activity)

        result.total_activities = data.get("pagination", {}).get("totalResults", len(result.activities))

        logger.info(f"✅ {len(result.activities)} activités trouvées")
        return result

    def get_product_all_activities(
        self,
        product_code: str,
        filters: str = "",
        max_pages: int = None,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> List[PublicActivity]:
        """
        Récupère toutes les activités d'un produit

        Args:
            product_code: Code du produit
            filters: Filtres optionnels
            max_pages: Nombre max de pages
            progress_callback: Callback(current_page, total_pages, last_name)

        Returns:
            Liste de toutes les activités
        """
        self._log_separator(f"ALL ACTIVITIES {product_code}")

        all_activities = []
        page = 1
        total_pages = None

        while True:
            result = self.get_product_activities(product_code, filters, page)

            if not result or not result.activities:
                break

            all_activities.extend(result.activities)

            # Calculer total pages
            if total_pages is None and result.total_activities:
                total_pages = (result.total_activities + result.page_size - 1) // result.page_size

            # Appliquer max_pages au total pour le callback
            effective_total = total_pages or page
            if max_pages:
                effective_total = min(effective_total, max_pages)

            if progress_callback:
                last_name = result.activities[-1].name[:30] if result.activities else ""
                # S'assurer que page <= effective_total pour eviter progress > 1.0
                safe_page = min(page, effective_total)
                progress_callback(safe_page, effective_total, last_name)

            # Vérifier pagination
            if len(result.activities) < result.page_size:
                break
            if max_pages and page >= max_pages:
                break

            page += 1

        logger.info(f"✅ Total: {len(all_activities)} activités en {page} pages")
        return all_activities

    def _parse_activity(self, data: Dict) -> PublicActivity:
        """Parse une activité depuis la réponse API"""
        # Log les clés disponibles pour debug (première activité seulement)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[ACTIVITY KEYS] {list(data.keys())}")

        # ID - plusieurs variantes possibles
        activity_id = (
            data.get("activityId") or
            data.get("id") or
            data.get("code") or
            ""
        )

        # Nom - plusieurs variantes possibles
        activity_name = (
            data.get("activityName") or
            data.get("name") or
            data.get("title") or
            ""
        )

        # Partenaire - plusieurs variantes possibles
        partner_name = (
            data.get("partnerName") or
            data.get("partner", {}).get("name", "") if isinstance(data.get("partner"), dict) else "" or
            data.get("partnerCompanyName") or
            ""
        )

        # Ville - plusieurs variantes possibles
        city = (
            data.get("city") or
            data.get("locationCity") or
            data.get("address", {}).get("city", "") if isinstance(data.get("address"), dict) else "" or
            ""
        )

        # Région - plusieurs variantes possibles
        region = (
            data.get("parentRegion") or
            data.get("region") or
            data.get("locationRegion") or
            ""
        )

        # Pays
        country = (
            data.get("country") or
            data.get("locationCountry") or
            ""
        )

        activity = PublicActivity(
            id=str(activity_id),
            name=activity_name,
            partner_name=partner_name,
            city=city,
            region=region,
            country=country,
            average_rating=data.get("activityCustomerAverageRating"),
            review_count=int(data.get("activityCustomerReviewQuantity", 0) or 0),
            raw_data=data,
        )

        # Coordonnées GPS - plusieurs variantes
        lat = data.get("latitude") or data.get("lat") or data.get("geoPoint", {}).get("latitude")
        lon = data.get("longitude") or data.get("lon") or data.get("lng") or data.get("geoPoint", {}).get("longitude")

        if lat:
            try:
                activity.latitude = float(lat)
            except (ValueError, TypeError):
                pass
        if lon:
            try:
                activity.longitude = float(lon)
            except (ValueError, TypeError):
                pass

        # Image
        images = data.get("images", [])
        if images:
            activity.image_url = images[0].get("url", "")

        return activity

    # ========================================================================
    # DÉTAILS D'UNE ACTIVITÉ (via redirection + HTML)
    # ========================================================================

    def get_activity_details(self, activity_code: str) -> Optional[Dict]:
        """
        Récupère les détails d'une activité en suivant la redirection /a/{code}
        puis en parsant le HTML de la page partenaire.

        Args:
            activity_code: Code de l'activité (ex: ANZCB1)

        Returns:
            Dict avec les infos extraites ou None si erreur
        """
        self._log_separator(f"ACTIVITY DETAILS {activity_code}")

        try:
            # Suivre la redirection /a/{code} -> /nom-partenaire/l/{partner_code}
            url = f"https://www.wonderbox.fr/a/{activity_code}"
            resp = self.session.get(url, allow_redirects=True, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"Erreur HTTP {resp.status_code} pour {activity_code}")
                return None

            # URL finale après redirection
            final_url = resp.url
            logger.debug(f"URL finale: {final_url}")

            # Extraire le code partenaire de l'URL (ex: /l/LL0W21)
            partner_code_match = re.search(r'/l/([A-Z0-9]+)$', final_url)
            partner_code = partner_code_match.group(1) if partner_code_match else ""

            # Parser le HTML
            soup = BeautifulSoup(resp.text, 'html.parser')

            details = {
                'activity_code': activity_code,
                'partner_code': partner_code,
                'partner_url': final_url,
                'name': '',
                'theme': '',
                'address': '',
                'city': '',
            }

            # Titre de la page
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Format: "Nom Partenaire - Ville | Wonderbox"
                if ' | ' in title_text:
                    details['name'] = title_text.split(' | ')[0].strip()

            # Extraire les données du dataLayer (GTM)
            scripts = soup.find_all('script', type='text/javascript')
            for script in scripts:
                if script.string and 'wbx_gtm_productDetail' in script.string:
                    # Extraire theme
                    theme_match = re.search(r"theme:\s*'([^']+)'", script.string)
                    if theme_match:
                        details['theme'] = theme_match.group(1)

                    # Extraire name (slug)
                    name_match = re.search(r"name:\s*'([^']+)'", script.string)
                    if name_match:
                        details['name_slug'] = name_match.group(1)

            logger.info(f"✅ Détails récupérés pour {activity_code}: {details.get('name', 'N/A')}")
            return details

        except Exception as e:
            logger.error(f"❌ Erreur get_activity_details: {e}")
            return None

    def enrich_activities_with_details(
        self,
        activities: List[PublicActivity],
        max_activities: int = None,
        progress_callback: Callable[[int, int, str], None] = None
    ) -> List[PublicActivity]:
        """
        Enrichit une liste d'activités avec les détails du partenaire.
        ATTENTION: Fait une requête HTTP par activité, peut être lent.

        Args:
            activities: Liste d'activités à enrichir
            max_activities: Nombre max d'activités à enrichir (None = toutes)
            progress_callback: Callback(current, total, name)

        Returns:
            Liste des activités enrichies
        """
        self._log_separator("ENRICH ACTIVITIES")

        total = min(len(activities), max_activities) if max_activities else len(activities)

        for i, activity in enumerate(activities[:total]):
            if progress_callback:
                progress_callback(i + 1, total, activity.id)

            if not activity.id:
                continue

            details = self.get_activity_details(activity.id)
            if details:
                activity.partner_code = details.get('partner_code', '')
                activity.partner_url = details.get('partner_url', '')
                activity.theme = details.get('theme', '')
                if not activity.name and details.get('name'):
                    activity.name = details.get('name', '')

        logger.info(f"✅ {total} activités enrichies")
        return activities

    # ========================================================================
    # DÉTAILS D'UN PARTENAIRE (via HTML)
    # ========================================================================

    def get_partner_details(self, partner_code: str) -> Optional[PublicPartner]:
        """
        Récupère les détails d'un partenaire en parsant le HTML de sa page.
        Extraction exhaustive de toutes les données disponibles.

        L'URL est construite à partir du code partenaire: /l/{partner_code}
        Exemple: https://www.wonderbox.fr/antik-spa-le-neubourg/l/LHIR01

        Args:
            partner_code: Code du partenaire (ex: LHIR01)

        Returns:
            PublicPartner avec les infos extraites ou None si erreur
        """
        self._log_separator(f"PARTNER DETAILS {partner_code}")
        import json
        from html import unescape

        try:
            # L'URL /l/{code} redirige vers la page complète du partenaire
            url = f"https://www.wonderbox.fr/l/{partner_code}"
            resp = self.session.get(url, allow_redirects=True, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"Erreur HTTP {resp.status_code} pour partenaire {partner_code}")
                return None

            final_url = str(resp.url)
            logger.debug(f"URL finale: {final_url}")

            # Parser le HTML
            soup = BeautifulSoup(resp.text, 'html.parser')

            partner = PublicPartner(
                code=partner_code,
                url=final_url,
                raw_html=resp.text[:10000],
            )

            # ================================================================
            # 1. SLUG depuis l'URL
            # ================================================================
            slug_match = re.search(r'wonderbox\.fr/([^/]+)/l/', final_url)
            if slug_match:
                partner.slug = slug_match.group(1)

            # ================================================================
            # 2. TITRE -> Nom et Ville
            # Format: "Antik Spa - Le Neubourg | Wonderbox"
            # ================================================================
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if ' | ' in title_text:
                    full_name = title_text.split(' | ')[0].strip()
                    if ' - ' in full_name:
                        parts = full_name.rsplit(' - ', 1)
                        partner.name = parts[0].strip()
                        partner.city = parts[1].strip()
                    else:
                        partner.name = full_name

            # ================================================================
            # 3. GTM dataLayer -> theme, category, slug
            # ================================================================
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'wbx_gtm_productDetail' in script.string:
                    # theme: 'relaxation'
                    theme_match = re.search(r"theme:\s*'([^']+)'", script.string)
                    if theme_match:
                        partner.theme = theme_match.group(1)

                    # dimension11: 'relaxation' (category)
                    cat_match = re.search(r"dimension11:\s*'([^']+)'", script.string)
                    if cat_match:
                        partner.category = cat_match.group(1)

                    # name: 'antik_spa' (slug)
                    name_match = re.search(r"name:\s*'([^']+)'", script.string)
                    if name_match:
                        partner.slug = partner.slug or name_match.group(1)
                    break

            # ================================================================
            # 4. DESCRIPTION - plusieurs sélecteurs possibles
            # ================================================================
            # Essayer .wbx-product-description-text via CSS selector (n'importe quel élément: div, p, span...)
            desc_elem = soup.select_one('.wbx-product-description-text')
            if desc_elem:
                partner.description = desc_elem.get_text(strip=True)
                logger.debug(f"Description trouvée via select_one (.wbx-product-description-text)")

            # Si pas trouvé, essayer avec find sur n'importe quel élément
            if not partner.description:
                desc_elem = soup.find(class_=lambda x: x and 'wbx-product-description-text' in str(x))
                if desc_elem:
                    partner.description = desc_elem.get_text(strip=True)
                    logger.debug(f"Description trouvée via find class_ lambda")

            # Dernier recours: chercher dans une classe contenant "description" (sauf col)
            if not partner.description:
                desc_elem = soup.find(class_=lambda x: x and 'description' in str(x).lower() and 'col' not in str(x).lower())
                if desc_elem:
                    partner.description = desc_elem.get_text(strip=True)
                    logger.debug(f"Description trouvée via fallback")

            if not partner.description:
                logger.warning(f"Description non trouvée pour {partner_code}")

            # ================================================================
            # 5. RATING - .rating avec data-rating et .rating__count
            # ================================================================
            rating_div = soup.find('div', class_='rating')
            if rating_div:
                data_rating = rating_div.get('data-rating')
                if data_rating:
                    try:
                        partner.average_rating = float(data_rating)
                    except (ValueError, TypeError):
                        pass

                # Nombre d'avis
                count_span = rating_div.find('span', class_='rating__count')
                if count_span:
                    count_text = count_span.get_text(strip=True)
                    # Format: "(123 avis)" ou "123"
                    count_match = re.search(r'(\d+)', count_text)
                    if count_match:
                        partner.review_count = int(count_match.group(1))

            # ================================================================
            # 6. CONTACT ET ADRESSE
            # ================================================================
            # Adresse - essayer .description-col__address d'abord (n'importe quel élément)
            address_elem = soup.select_one('.description-col__address')
            if address_elem:
                partner.address = address_elem.get_text(strip=True)
                logger.debug(f"Adresse trouvée via select_one (.description-col__address)")

            # Si pas trouvé, essayer avec class_ lambda sur n'importe quel élément
            if not partner.address:
                address_elem = soup.find(class_=lambda x: x and 'description-col__address' in str(x))
                if address_elem:
                    partner.address = address_elem.get_text(strip=True)
                    logger.debug(f"Adresse trouvée via find class_ lambda")

            # Si toujours pas trouvé, essayer .wbx-contact-item--address
            if not partner.address:
                address_item = soup.select_one('.wbx-contact-item--address')
                if address_item:
                    content = address_item.select_one('.wbx-contact-item__content')
                    if content:
                        partner.address = content.get_text(strip=True)
                        logger.debug(f"Adresse trouvée via wbx-contact-item")

            if not partner.address:
                logger.warning(f"Adresse non trouvée pour {partner_code}")

            # Téléphone
            phone_item = soup.find('li', class_='wbx-contact-item--phone')
            if phone_item:
                content = phone_item.find('span', class_='wbx-contact-item__content')
                if content:
                    partner.phone = content.get_text(strip=True)

            # Site web
            link_item = soup.find('li', class_='wbx-contact-item--link')
            if link_item:
                content = link_item.find('span', class_='wbx-contact-item__content')
                if content:
                    link_tag = content.find('a')
                    if link_tag:
                        partner.website = link_tag.get('href', '') or link_tag.get_text(strip=True)

            # ================================================================
            # 7. IMAGES - .wbx-product-images-main__slide img
            # ================================================================
            image_slides = soup.find_all('div', class_='wbx-product-images-main__slide')
            images = []
            for slide in image_slides:
                img = slide.find('img')
                if img:
                    src = img.get('data-lazy') or img.get('src') or ''
                    if src and src.startswith('http'):
                        images.append(src)
            if images:
                partner.images = images

            # ================================================================
            # 8. COFFRETS ASSOCIÉS - .wbx-section-box a[href*="/b/"]
            # ================================================================
            product_links = soup.find_all('a', href=re.compile(r'/b/[A-Z0-9]+'))
            product_codes = set()
            for link in product_links:
                href = link.get('href', '')
                match = re.search(r'/b/([A-Z0-9]+)', href)
                if match:
                    product_codes.add(match.group(1))
            partner.products = list(product_codes)

            # ================================================================
            # 9. ACTIVITÉS - div.show-popin-add[data-gtm-box]
            # Extraction des activités du partenaire depuis les données GTM
            # ================================================================
            activity_divs = soup.find_all('div', class_='show-popin-add', attrs={'data-gtm-box': True})
            activities = []

            for div in activity_divs:
                gtm_data = div.get('data-gtm-box', '')
                if not gtm_data:
                    continue

                try:
                    # Décoder les entités HTML (&quot; -> ")
                    gtm_json = unescape(gtm_data)
                    gtm_obj = json.loads(gtm_json)

                    # Extraire les produits (activités)
                    products_data = gtm_obj.get('ecommerce', {}).get('add', {}).get('products', [])
                    for prod in products_data:
                        activity = PartnerActivity(
                            id=prod.get('id', ''),
                            name=prod.get('name', ''),
                            theme=prod.get('theme', ''),
                            subtheme=prod.get('subtheme', ''),
                            category=prod.get('dimension11', ''),
                            type=prod.get('dimension12', ''),
                            department=prod.get('dimension13', ''),
                        )

                        # Prix
                        price = prod.get('price')
                        if price is not None:
                            try:
                                activity.price = float(price)
                            except (ValueError, TypeError):
                                pass

                        price_discount = prod.get('price_discount')
                        if price_discount is not None:
                            try:
                                activity.price_discount = float(price_discount)
                            except (ValueError, TypeError):
                                pass

                        activities.append(activity)

                except json.JSONDecodeError as e:
                    logger.debug(f"Erreur parsing GTM JSON: {e}")
                    continue

            partner.activities = activities

            # ================================================================
            # 10. INFOS SUPPLÉMENTAIRES depuis les sections
            # ================================================================
            # Points forts / Highlights
            highlights_section = soup.find('div', class_=re.compile(r'highlight|point', re.I))
            if highlights_section:
                items = highlights_section.find_all('li')
                partner.highlights = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]

            # Inclus dans l'offre
            included_section = soup.find('div', class_=re.compile(r'includ|compris', re.I))
            if included_section:
                items = included_section.find_all('li')
                partner.included = [li.get_text(strip=True) for li in items if li.get_text(strip=True)]

            # Infos pratiques
            practical_section = soup.find('div', class_=re.compile(r'practical|pratique|info', re.I))
            if practical_section:
                partner.practical_info = practical_section.get_text(strip=True)[:2000]

            # ================================================================
            # 11. DÉPARTEMENT depuis les activités ou l'adresse
            # ================================================================
            if activities and activities[0].department:
                # Format: "de27" -> "27"
                dept = activities[0].department
                if dept.startswith('de'):
                    partner.department = dept[2:]
                else:
                    partner.department = dept

            # Si le subtheme n'est pas défini au niveau partner, prendre celui de la première activité
            if not partner.subtheme and activities:
                partner.subtheme = activities[0].subtheme

            # ================================================================
            # 12. AVIS CLIENTS - via /p/{code}/reviews
            # ================================================================
            reviews, avg_rating, total_reviews, rating_dist = self.get_partner_reviews(partner_code)
            partner.reviews = reviews
            partner.rating_distribution = rating_dist
            # Mettre à jour la note et le nombre d'avis si on a des données plus précises
            if avg_rating is not None:
                partner.average_rating = avg_rating
            if total_reviews > 0:
                partner.review_count = total_reviews

            logger.info(f"✅ Partenaire récupéré: {partner.name or partner.code} - {len(activities)} activités - {len(reviews)} avis")
            return partner

        except Exception as e:
            logger.error(f"❌ Erreur get_partner_details: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def get_partner_reviews(self, partner_code: str, max_pages: int = 5) -> Tuple[List[PartnerReview], Optional[float], int, Dict[int, int]]:
        """
        Récupère les avis d'un partenaire via l'endpoint /p/{code}/reviews

        Args:
            partner_code: Code du partenaire (ex: LHIR01)
            max_pages: Nombre max de pages à récupérer (10 avis par page)

        Returns:
            Tuple: (liste des avis, note moyenne, nombre total d'avis, distribution des notes)
        """
        self._log_separator(f"PARTNER REVIEWS {partner_code}")

        reviews = []
        average_rating = None
        total_reviews = 0
        rating_distribution = {}  # {5: 91, 4: 5, ...} en pourcentage

        try:
            # Première page pour obtenir les stats globales
            url = f"https://www.wonderbox.fr/p/{partner_code}/reviews"
            resp = self.session.get(url, timeout=15)

            if resp.status_code != 200:
                logger.warning(f"Erreur HTTP {resp.status_code} pour reviews {partner_code}")
                return reviews, average_rating, total_reviews, rating_distribution

            soup = BeautifulSoup(resp.text, 'html.parser')

            # ================================================================
            # STATS GLOBALES
            # ================================================================
            # Nombre total d'avis
            total_input = soup.select_one('input.totalNumberOfReviews')
            if total_input:
                try:
                    total_reviews = int(total_input.get('value', 0))
                except (ValueError, TypeError):
                    pass

            # Note moyenne (format: "4,8/5")
            avg_elem = soup.select_one('.reviews-avg')
            if avg_elem:
                avg_text = avg_elem.get_text(strip=True)
                match = re.search(r'([\d,]+)/5', avg_text)
                if match:
                    try:
                        average_rating = float(match.group(1).replace(',', '.'))
                    except (ValueError, TypeError):
                        pass

            # Distribution des notes (pourcentage par étoile)
            rating_lines = soup.select('li.rating-line')
            for line in rating_lines:
                rating_attr = line.get('data-bazaarvoice-rating')
                if rating_attr:
                    try:
                        star_count = int(rating_attr)
                        # Chercher le pourcentage
                        pct_elem = line.select_one('.text-percentage')
                        if pct_elem:
                            pct_text = pct_elem.get_text(strip=True)
                            if pct_text == '-':
                                rating_distribution[star_count] = 0
                            else:
                                pct_match = re.search(r'(\d+)', pct_text)
                                if pct_match:
                                    rating_distribution[star_count] = int(pct_match.group(1))
                    except (ValueError, TypeError):
                        pass

            # ================================================================
            # PARSING DES AVIS
            # ================================================================
            def parse_reviews_from_soup(soup_obj):
                """Parse les avis depuis un objet BeautifulSoup"""
                parsed_reviews = []
                comment_divs = soup_obj.select('.wbx-comment')

                for comment in comment_divs:
                    review = PartnerReview()

                    # ID de l'avis (depuis le bouton de signalement)
                    report_btn = comment.select_one('button[contentId]')
                    if report_btn:
                        review.id = report_btn.get('contentId', '')

                    # Note (compter les étoiles pleines)
                    stars = comment.select('.review-rating .icon-nsw-star.full')
                    review.rating = len(stars)

                    # Titre
                    title_elem = comment.select_one('.review-title')
                    if title_elem:
                        review.title = title_elem.get_text(strip=True)

                    # Commentaire
                    comment_elem = comment.select_one('.review-comment')
                    if comment_elem:
                        review.comment = comment_elem.get_text(strip=True)

                    # Nom d'utilisateur
                    username_elem = comment.select_one('.review-username--name')
                    if username_elem:
                        review.username = username_elem.get_text(strip=True)

                    # Date de l'avis
                    date_elem = comment.select_one('.review-date--date')
                    if date_elem:
                        review.date = date_elem.get_text(strip=True)

                    # Date de l'expérience
                    exp_elem = comment.select_one('.reviews-experience')
                    if exp_elem:
                        exp_text = exp_elem.get_text(strip=True)
                        # Format: "Expérience réalisée en juillet 2022"
                        match = re.search(r'en\s+(.+)$', exp_text)
                        if match:
                            review.experience_date = match.group(1)

                    # Activité liée
                    activity_link = comment.select_one('.review-link a')
                    if activity_link:
                        review.activity_name = activity_link.get('title', '') or activity_link.get_text(strip=True)
                        href = activity_link.get('href', '')
                        # Extraire le code activité de l'URL
                        code_match = re.search(r'/a/([A-Z0-9]+)', href)
                        if code_match:
                            review.activity_code = code_match.group(1)

                    # Nombre de votes utiles
                    helpful_elem = comment.select_one('.like-amount[data-vote]')
                    if helpful_elem:
                        try:
                            review.helpful_count = int(helpful_elem.get('data-vote', 0))
                        except (ValueError, TypeError):
                            pass

                    if review.comment or review.title:  # Au moins un contenu
                        parsed_reviews.append(review)

                return parsed_reviews

            # Parser la première page
            reviews.extend(parse_reviews_from_soup(soup))

            # Pagination - récupérer les pages suivantes si nécessaire
            page = 2
            while len(reviews) < total_reviews and page <= max_pages:
                # L'API utilise un offset de 10 par page
                paginate_url = f"https://www.wonderbox.fr/p/{partner_code}/reviews?page={page * 10}"
                resp = self.session.get(paginate_url, timeout=15)

                if resp.status_code != 200:
                    break

                page_soup = BeautifulSoup(resp.text, 'html.parser')
                new_reviews = parse_reviews_from_soup(page_soup)

                if not new_reviews:
                    break

                reviews.extend(new_reviews)
                page += 1

            logger.info(f"✅ {len(reviews)}/{total_reviews} avis récupérés pour {partner_code}")
            return reviews, average_rating, total_reviews, rating_distribution

        except Exception as e:
            logger.error(f"❌ Erreur get_partner_reviews: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return reviews, average_rating, total_reviews, rating_distribution

    # ========================================================================
    # RÉCUPÉRATION DES FACETTES (FILTRES DISPONIBLES)
    # ========================================================================

    def get_category_facets(self, category_code: str) -> List[Dict]:
        """
        Récupère les facettes (filtres) disponibles pour une catégorie

        Returns:
            Liste des facettes avec leurs valeurs
        """
        result = self.search_category(category_code, page_size=1)
        return result.facets if result else []

    def get_product_facets(self, product_code: str) -> List[Dict]:
        """
        Récupère les facettes (filtres) disponibles pour les activités d'un produit

        Returns:
            Liste des facettes avec leurs valeurs
        """
        result = self.get_product_activities(product_code, page_size=1)
        return result.facets if result else []

    # ========================================================================
    # UTILITAIRES
    # ========================================================================

    def test_connection(self) -> Tuple[bool, str]:
        """Teste la connexion à l'API publique"""
        self._log_separator("TEST CONNEXION")

        try:
            # Test simple: recherche dans une catégorie connue
            url = f"{self.BASE_URL}/products/search"
            resp = self.session.get(url, params={"query": "/c/155661"}, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if "products" in data:
                    count = len(data.get("products", []))
                    logger.info(f"✅ API accessible - {count} produits")
                    return True, f"API accessible ({count} produits)"

            return False, f"Erreur HTTP {resp.status_code}"

        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return False, str(e)
