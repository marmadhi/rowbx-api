"""
Scraper enrichi pour les produits (Box) - Avis et détails d'activités
======================================================================
"""
import logging
import re
import json
import html as html_module
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from .base_public_scraper import PublicServiceBase
from common.models import (
    ProductReview, ProductReviewStats, ActivityQuickView, ProductInfo
)

logger = logging.getLogger("ProductReviewsScraper")


class ProductBoxScraper(PublicServiceBase):
    """Scraper complet pour les produits (Box) avec avis et activités enrichies"""

    def extract_product_code(self, url_or_code: str) -> Optional[str]:
        """
        Extrait le code produit depuis une URL ou le retourne directement.

        Supporte:
        - Code direct: BZZN01, A39H01
        - URL produit: https://www.wonderbox.fr/pour-un-couple-extra/b/BZZN01
        - URL avec slug: https://www.wonderbox.fr/b/pour-un-couple-extra
        """
        url_or_code = url_or_code.strip()

        # Si c'est déjà un code Wonderbox (format: lettres + chiffres, ex: BZZN01, A39H01)
        # Le code doit contenir au moins une lettre ET au moins un chiffre
        if re.match(r'^[A-Z0-9]{4,8}$', url_or_code.upper()):
            # Vérifier qu'il contient bien des chiffres (pas juste des lettres comme "POUR")
            if re.search(r'\d', url_or_code):
                return url_or_code.upper()

        # Extraction depuis URL avec /b/CODE (code alphanumérique avec chiffres)
        match = re.search(r'/b/([A-Z]+\d+[A-Z0-9]*)', url_or_code, re.I)
        if match:
            return match.group(1).upper()

        # Si c'est une URL Wonderbox, scraper la page pour trouver le code
        if 'wonderbox.fr' in url_or_code:
            return self._extract_code_from_page(url_or_code)

        return None

    def _extract_code_from_page(self, url: str) -> Optional[str]:
        """Extrait le code produit depuis le HTML de la page"""
        self._log_separator(f"EXTRACT CODE FROM {url}")

        html_content = self._fetch_html(url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # Méthode 1: Input caché productCodePost (le plus fiable)
        product_code_input = soup.find('input', {'name': 'productCodePost'})
        if product_code_input:
            code = product_code_input.get('value', '').strip()
            if code:
                logger.debug(f"Code extrait via productCodePost: {code}")
                return code.upper()

        # Méthode 2: Bouton addToCart avec data-config
        add_to_cart = soup.find('button', {'id': 'addToCartButton'})
        if add_to_cart:
            data_config = add_to_cart.get('data-config', '')
            if data_config:
                try:
                    decoded = html_module.unescape(data_config)
                    config = json.loads(decoded)
                    products = config.get('ecommerce', {}).get('add', {}).get('products', [])
                    if products:
                        code = products[0].get('id', '')
                        if code:
                            logger.debug(f"Code extrait via addToCart: {code}")
                            return code.upper()
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Erreur parsing data-config: {e}")

        # Méthode 3: Script GTM wbx_gtm_productDetail
        for script in soup.find_all('script'):
            if script.string and 'wbx_gtm_productDetail' in script.string:
                match = re.search(r'"id"\s*:\s*"([A-Z0-9]+)"', script.string)
                if match:
                    logger.debug(f"Code extrait via GTM: {match.group(1)}")
                    return match.group(1).upper()

        # Méthode 4: URL canonique avec /b/CODE
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical:
            href = canonical.get('href', '')
            match = re.search(r'/b/([A-Z0-9]+)', href, re.I)
            if match:
                logger.debug(f"Code extrait via canonical: {match.group(1)}")
                return match.group(1).upper()

        # Méthode 5: Regex dans le HTML brut pour productCode
        match = re.search(r'productCode["\']?\s*[:=]\s*["\']([A-Z0-9]{4,8})["\']', html_content, re.I)
        if match:
            logger.debug(f"Code extrait via regex: {match.group(1)}")
            return match.group(1).upper()

        logger.warning(f"Impossible d'extraire le code produit depuis {url}")
        return None

    def get_product_info(self, url_or_code: str) -> Optional[ProductInfo]:
        """
        Récupère les informations du produit depuis la page.

        Args:
            url_or_code: URL complète ou code produit

        Returns:
            ProductInfo avec code, prix, thème, etc.
        """
        # Si c'est une URL, l'utiliser directement pour scraper
        if 'wonderbox.fr' in url_or_code:
            return self._scrape_product_info_from_url(url_or_code)

        # Sinon c'est un code, construire l'URL
        url = f"{self.SITE_URL}/b/{url_or_code}"
        return self._scrape_product_info_from_url(url)

    def _scrape_product_info_from_url(self, url: str) -> Optional[ProductInfo]:
        """Scrape les infos produit depuis l'URL"""
        self._log_separator(f"PRODUCT INFO FROM {url}")

        html_content = self._fetch_html(url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        info = ProductInfo()

        # Méthode 1: Extraction depuis addToCart button (source principale)
        add_to_cart = soup.find('button', {'id': 'addToCartButton'})
        if add_to_cart:
            data_config = add_to_cart.get('data-config', '')
            if data_config:
                try:
                    decoded = html_module.unescape(data_config)
                    config = json.loads(decoded)
                    products = config.get('ecommerce', {}).get('add', {}).get('products', [])
                    if products:
                        p = products[0]
                        info.code = p.get('id', '').upper()
                        info.name = p.get('name', '').replace('_', ' ').title()
                        info.brand = p.get('brand', '')
                        info.theme = p.get('theme', '')
                        info.subtheme = p.get('subtheme', '')
                        info.price = float(p.get('price', 0)) if p.get('price') else None
                        info.price_discount = float(p.get('price_discount', 0)) if p.get('price_discount') else None
                        info.category = p.get('dimension11', '')
                        info.product_type = p.get('dimension10', '')
                        info.dimensions = {
                            'dimension10': p.get('dimension10', ''),
                            'dimension11': p.get('dimension11', ''),
                            'dimension12': p.get('dimension12', ''),
                            'dimension13': p.get('dimension13', ''),
                            'dimension14': p.get('dimension14', ''),
                            'dimension15': p.get('dimension15', ''),
                            'dimension39': p.get('dimension39', ''),
                            'dimension40': p.get('dimension40', ''),
                            'dimension41': p.get('dimension41', ''),
                            'dimension42': p.get('dimension42', ''),
                            'dimension43': p.get('dimension43', ''),
                            'dimension44': p.get('dimension44', ''),
                            'dimension45': p.get('dimension45', ''),
                            'dimension46': p.get('dimension46', ''),
                        }
                        info.raw_data = p
                        logger.debug(f"Product info extrait via addToCart: {info.code}")
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Erreur parsing product info: {e}")

        # Méthode 2: Fallback via input productCodePost
        if not info.code:
            product_code_input = soup.find('input', {'name': 'productCodePost'})
            if product_code_input:
                info.code = product_code_input.get('value', '').strip().upper()
                logger.debug(f"Code extrait via productCodePost: {info.code}")

        # Extraction du slug depuis l'URL
        match = re.search(r'wonderbox\.fr/([^/]+)(?:/b/|$)', url)
        if match:
            slug = match.group(1)
            if slug not in ['b', 'p', 'a', 'l']:  # Exclure les préfixes de routes
                info.slug = slug

        # Extraction du nom depuis le titre de la page si non trouvé
        if not info.name:
            title = soup.find('title')
            if title:
                # Format typique: "Nom du produit | Wonderbox"
                title_text = title.get_text(strip=True)
                info.name = title_text.split('|')[0].strip()

        return info if info.code else None

    def get_product_reviews(
        self,
        product_code: str,
        rating: Optional[int] = None,
        max_pages: int = 10
    ) -> Tuple[List[ProductReview], ProductReviewStats]:
        """
        Récupère les avis d'un produit, optionnellement filtrés par rating.

        Args:
            product_code: Code du produit (ex: BZZN01)
            rating: Filtre par étoiles (1-5), None pour tous
            max_pages: Nombre max de pages à scraper
        """
        self._log_separator(f"PRODUCT REVIEWS {product_code} (rating={rating})")

        all_reviews = []
        stats = ProductReviewStats()

        # URL de base
        base_url = f"{self.SITE_URL}/p/{product_code}/reviews"
        params = {}
        if rating:
            params['rating'] = str(rating)

        # Première page
        url = base_url
        if params:
            url += '?' + '&'.join(f"{k}={v}" for k, v in params.items())

        html_content = self._fetch_html(url)
        if not html_content:
            return [], stats

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extraction des stats
        stats = self._extract_review_stats(soup)

        # Parse première page
        reviews = self._parse_product_reviews(soup)
        all_reviews.extend(reviews)

        # Pagination
        page = 2
        while len(all_reviews) < stats.total_reviews and page <= max_pages:
            page_params = params.copy()
            page_params['page'] = str(page * 5)  # Offset de 5 par page

            page_url = base_url + '?' + '&'.join(f"{k}={v}" for k, v in page_params.items())
            next_html = self._fetch_html(page_url)

            if not next_html:
                break

            next_soup = BeautifulSoup(next_html, 'html.parser')
            new_reviews = self._parse_product_reviews(next_soup)

            if not new_reviews:
                break

            all_reviews.extend(new_reviews)
            page += 1
            logger.debug(f"Page {page - 1}: {len(new_reviews)} avis")

        return all_reviews, stats

    def get_all_reviews_by_rating(
        self,
        product_code: str,
        max_pages_per_rating: int = 5
    ) -> Tuple[Dict[int, List[ProductReview]], ProductReviewStats]:
        """
        Récupère tous les avis groupés par rating (1-5 étoiles).

        Returns:
            Dictionnaire {rating: [reviews]} et stats globales
        """
        self._log_separator(f"ALL REVIEWS BY RATING {product_code}")

        reviews_by_rating = {}
        global_stats = None

        for rating in [5, 4, 3, 2, 1]:
            reviews, stats = self.get_product_reviews(
                product_code,
                rating=rating,
                max_pages=max_pages_per_rating
            )
            reviews_by_rating[rating] = reviews

            if global_stats is None:
                global_stats = stats

            logger.info(f"Rating {rating}: {len(reviews)} avis")

        return reviews_by_rating, global_stats or ProductReviewStats()

    def _extract_review_stats(self, soup: BeautifulSoup) -> ProductReviewStats:
        """Extrait les statistiques des avis"""
        stats = ProductReviewStats()

        # Total reviews
        total_input = soup.select_one('input.totalNumberOfReviews')
        if total_input:
            try:
                stats.total_reviews = int(total_input.get('value', 0))
            except (ValueError, TypeError):
                pass

        # Average rating
        avg_elem = soup.select_one('.reviews-avg')
        if avg_elem:
            match = re.search(r'([\d,]+)/5', avg_elem.get_text())
            if match:
                try:
                    stats.average_rating = float(match.group(1).replace(',', '.'))
                except (ValueError, TypeError):
                    pass

        # Rating distribution
        for li in soup.select('.list-ratings .rating-line'):
            rating_attr = li.get('data-bazaarvoice-rating')
            if rating_attr:
                try:
                    rating = int(rating_attr)
                    # Pourcentage
                    pct_elem = li.select_one('.text-percentage')
                    if pct_elem:
                        pct_text = pct_elem.get_text(strip=True)
                        match = re.search(r'(\d+)', pct_text)
                        if match:
                            stats.rating_percentages[rating] = int(match.group(1))
                            # Calcul du nombre d'avis pour ce rating
                            if stats.total_reviews:
                                stats.rating_distribution[rating] = int(
                                    stats.total_reviews * int(match.group(1)) / 100
                                )
                except (ValueError, TypeError):
                    pass

        return stats

    def _parse_product_reviews(self, soup: BeautifulSoup) -> List[ProductReview]:
        """Parse les avis depuis le HTML"""
        reviews = []

        for comment in soup.select('.wbx-comment'):
            review = ProductReview()

            # ID
            content_id = comment.select_one('button[contentId]')
            if content_id:
                review.id = content_id.get('contentId', '')

            # Rating (nombre d'étoiles pleines)
            stars = comment.select('.review-rating .icon-nsw-star.full')
            review.rating = len(stars)

            # Titre
            title_elem = comment.select_one('.review-title')
            if title_elem:
                review.title = title_elem.get_text(strip=True)

            # Commentaire
            body = comment.select_one('.review-comment')
            if body:
                review.comment = body.get_text(strip=True)

            # Username
            user = comment.select_one('.review-username--name')
            if user:
                review.username = user.get_text(strip=True)

            # Date
            date_elem = comment.select_one('.review-date--date')
            if date_elem:
                review.date = date_elem.get_text(strip=True)

            # Date d'expérience
            exp_elem = comment.select_one('.reviews-experience')
            if exp_elem:
                review.experience_date = exp_elem.get_text(strip=True)

            # Activité liée
            act_link = comment.select_one('.review-link a')
            if act_link:
                review.activity_name = act_link.get('title', '') or act_link.get_text(strip=True)
                review.activity_url = act_link.get('href', '')
                # Extraire le code activité
                match = re.search(r'/a/([A-Z0-9]+)', review.activity_url)
                if match:
                    review.activity_code = match.group(1)

            # Votes utiles
            like_elem = comment.select_one('.like-amount')
            if like_elem:
                try:
                    review.helpful_count = int(like_elem.get('data-vote', 0))
                except (ValueError, TypeError):
                    pass

            reviews.append(review)

        return reviews

    def get_activity_details(
        self,
        activity_id: str,
        box_code: str,
        product_slug: str = ""
    ) -> Optional[ActivityQuickView]:
        """
        Récupère les détails complets d'une activité via quickActivityView.

        Args:
            activity_id: Code de l'activité (ex: A39H01)
            box_code: Code du produit (ex: BZZN01)
            product_slug: Slug du produit (ex: pour-un-couple-extra)
        """
        self._log_separator(f"ACTIVITY DETAILS {activity_id}")

        # Construction URL
        if not product_slug:
            product_slug = "common"

        url = f"{self.SITE_URL}/{product_slug}/a/{activity_id}/quickActivityView"
        params = {
            "boxCode": box_code,
            "activityUrl": f"/{product_slug}/a/{activity_id}"
        }

        try:
            resp = self.session.get(
                url,
                params=params,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=15
            )
            if resp.status_code != 200:
                logger.warning(f"QuickView failed: {resp.status_code}")
                return None

            return self._parse_activity_quickview(resp.text, activity_id, box_code)

        except RequestException as e:
            logger.error(f"Erreur QuickView: {e}")
            return None

    def _parse_activity_quickview(
        self,
        html_content: str,
        activity_id: str,
        box_code: str
    ) -> ActivityQuickView:
        """Parse les détails d'une activité depuis le HTML quickActivityView"""
        soup = BeautifulSoup(html_content, 'html.parser')
        activity = ActivityQuickView(id=activity_id, box_code=box_code)

        # 1. Data-config JSON (contient theme, subtheme, prix, etc.)
        activity_top = soup.find('div', {'id': 'js-activity-popin'})
        if activity_top:
            data_config = activity_top.get('data-config', '')
            if data_config:
                try:
                    config = json.loads(data_config.strip())
                    product = config.get('product', {})
                    activity.name = product.get('name', '')
                    activity.theme = product.get('theme', '')
                    activity.subtheme = product.get('subtheme', '')
                    activity.price = float(product.get('unitprice_ati', 0)) if product.get('unitprice_ati') else None
                    activity.price_discount = float(product.get('discount_ati', 0)) if product.get('discount_ati') else None
                    activity.sales_type = product.get('sales_type', '')
                    activity.raw_data = config
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.debug(f"Erreur parsing data-config: {e}")

        # 2. Titre H1
        h1 = soup.find('h1')
        if h1 and not activity.name:
            activity.name = h1.get_text(strip=True)

        # 3. Rating et reviews
        rating_div = soup.select_one('.rating')
        if rating_div:
            stars = rating_div.select('.icon-nsw-star.full')
            half_stars = rating_div.select('.icon-half-star')
            activity.rating = len(stars) + (0.5 if half_stars else 0)

            count_elem = rating_div.select_one('.count')
            if count_elem:
                match = re.search(r'(\d+)', count_elem.get_text())
                if match:
                    activity.review_count = int(match.group(1))

        # 4. Description
        summary = soup.select_one('.activity-summary')
        if summary:
            activity.description = summary.get_text(strip=True)

        # 5. Programme
        program_list = soup.select('.program ul li')
        activity.program = [li.get_text(strip=True) for li in program_list]

        # 6. Participants
        participants = soup.select_one('.icon-user-2')
        if participants:
            activity.participants = participants.get_text(strip=True)

        # 7. Localisation
        loc_elem = soup.select_one('.access .attributes-label')
        if loc_elem:
            parent = loc_elem.parent
            if parent:
                activity.location = parent.get_text(strip=True).replace('Localisation :', '').strip()

        addr_li = soup.select('.access ul li')
        for li in addr_li:
            text = li.get_text(strip=True)
            if 'Adresse' in text:
                activity.address = text.replace('Adresse :', '').strip()

        # 8. À proximité
        nearby_li = soup.select('.discover ul li')
        for li in nearby_li:
            text = li.get_text(strip=True)
            if 'proximité' in text:
                activity.nearby = text.replace('À proximité :', '').strip()

        # 9. Informations pratiques
        practical_lis = soup.select('.popin-activity__content ul li')
        activity.practical_info = [li.get_text(strip=True) for li in practical_lis]

        # 10. Images
        for img in soup.select('.swiper-slide img'):
            src = img.get('src', '')
            if src and 'placeholder' not in src:
                # Construire URL complète
                if src.startswith('/'):
                    src = f"{self.SITE_URL}{src}"
                if src not in activity.images:
                    activity.images.append(src)

        # 11. Coordonnées GPS
        map_view = soup.select_one('.map-view')
        if map_view:
            try:
                activity.latitude = float(map_view.get('data-lat', 0))
                activity.longitude = float(map_view.get('data-lng', 0))
            except (ValueError, TypeError):
                pass

        # 12. Coup de coeur
        heartstroke = soup.select_one('.heartstroke')
        activity.is_favorite = heartstroke is not None

        # 13. Partner link
        partner_link = soup.find('a', href=re.compile(r'/l/([A-Z0-9]+)'))
        if partner_link:
            activity.partner_url = partner_link.get('href', '')
            match = re.search(r'/l/([A-Z0-9]+)', activity.partner_url)
            if match:
                activity.partner_code = match.group(1)

        return activity
