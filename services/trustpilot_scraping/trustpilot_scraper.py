import logging
import requests
import re
import json
from typing import List, Optional, Tuple, Dict
from bs4 import BeautifulSoup
from common.models import TrustpilotReview

logger = logging.getLogger("TrustpilotScraper")

class TrustpilotScraper:
    """Scraper pour Trustpilot"""
    
    BASE_URL = "https://fr.trustpilot.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
        
    def get_reviews(
        self,
        domain: str,
        pages: int = 1,
        stars: List[int] = None,
        search: str = None
    ) -> Tuple[List[TrustpilotReview], Optional[Dict]]:
        """
        Récupère les avis pour un domaine avec filtres optionnels.

        Args:
            domain: Domaine à scraper (ex: www.wonderbox.fr)
            pages: Nombre de pages à scraper
            stars: Liste des notes à filtrer (ex: [4, 5] pour 4 et 5 étoiles)
            search: Mot-clé de recherche (ex: "massage")

        Returns:
            Tuple (liste des avis, infos business unit)
        """
        all_reviews = []
        business_info = None

        # Construction des paramètres
        params = {}
        if stars:
            params['stars'] = ",".join(map(str, stars))
        if search:
            params['search'] = search

        for page in range(1, pages + 1):
            url = f"{self.BASE_URL}/review/{domain}"
            current_params = params.copy()
            if page > 1:
                current_params['page'] = page

            try:
                logger.info(f"Scraping Trustpilot {domain} page {page}" +
                           (f" search='{search}'" if search else "") +
                           (f" stars={stars}" if stars else ""))
                resp = self.session.get(url, params=current_params, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Stop: HTTP {resp.status_code}")
                    break

                reviews, page_business_info = self._parse_reviews_page(resp.text)

                # Garder les infos business de la première page
                if business_info is None and page_business_info:
                    business_info = page_business_info

                if not reviews:
                    break

                all_reviews.extend(reviews)

            except Exception as e:
                logger.error(f"Erreur scraping: {e}")
                break

        return all_reviews, business_info

    def search_reviews(
        self,
        domain: str,
        keyword: str,
        pages: int = 5,
        stars: List[int] = None
    ) -> Tuple[List[TrustpilotReview], Optional[Dict]]:
        """
        Recherche des avis contenant un mot-clé spécifique.

        Args:
            domain: Domaine à scraper
            keyword: Mot-clé à rechercher
            pages: Nombre max de pages
            stars: Filtre par étoiles optionnel

        Returns:
            Tuple (avis correspondants, infos business)
        """
        return self.get_reviews(domain, pages=pages, stars=stars, search=keyword)
        
    def _parse_reviews_page(self, html: str) -> Tuple[List[TrustpilotReview], Optional[Dict]]:
        """
        Parse une page d'avis Trustpilot.

        Returns:
            Tuple (liste des avis, infos business unit)
        """
        soup = BeautifulSoup(html, 'html.parser')
        reviews = []
        business_info = None

        # Approche 1: Next.js DATA (recommandée)
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            try:
                data = json.loads(script.string)
                props = data.get('props', {}).get('pageProps', {})

                # Extraire les infos business
                bu = props.get('businessUnit', {})
                if bu:
                    business_info = {
                        'id': bu.get('id', ''),
                        'displayName': bu.get('displayName', ''),
                        'identifyingName': bu.get('identifyingName', ''),
                        'numberOfReviews': bu.get('numberOfReviews', 0),
                        'trustScore': bu.get('trustScore', 0),
                        'stars': bu.get('stars', 0),
                        'websiteUrl': bu.get('websiteUrl', ''),
                        'categories': bu.get('categories', []),
                        'isClaimed': bu.get('isClaimed', False),
                        'activity': bu.get('activity', {}),
                    }

                # Extraire les avis
                reviews_data = props.get('reviews', [])

                for r in reviews_data:
                    # Nettoyer le HTML des highlights de recherche (<em>...</em>)
                    title_raw = r.get('title', '')
                    content_raw = r.get('text', '')
                    title_clean = self._strip_html_tags(title_raw)
                    content_clean = self._strip_html_tags(content_raw)

                    review = TrustpilotReview(
                        id=r.get('id', ''),
                        consumer_name=r.get('consumer', {}).get('displayName', ''),
                        rating=r.get('rating', 0),
                        title=title_clean,
                        content=content_clean,
                        date_published=r.get('dates', {}).get('publishedDate', ''),
                        date_experienced=r.get('dates', {}).get('experiencedDate', ''),
                        likes=r.get('likes', 0),
                    )

                    # Garder le titre/contenu avec highlights pour recherche
                    if '<em>' in title_raw or '<em>' in content_raw:
                        review.url = f"highlight:{title_raw}"  # Hack pour stocker le highlight

                    # Réponse de l'entreprise
                    if r.get('reply'):
                        review.reply_content = r['reply'].get('message', '')
                        review.reply_date = r['reply'].get('publishedDate', '')

                    # Infos consommateur enrichies
                    consumer = r.get('consumer', {})
                    if consumer.get('countryCode'):
                        review.url = f"country:{consumer.get('countryCode')}"

                    reviews.append(review)

                if reviews:
                    return reviews, business_info

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Parse error: {e}")

        # Approche 2: HTML classes (Fallback)
        articles = soup.find_all('article')
        for art in articles:
            # Rating
            star_img = art.find('img', alt=re.compile(r'Note : \d'))
            rating = 0
            if star_img:
                match = re.search(r'Note : (\d)', star_img['alt'])
                if match:
                    rating = int(match.group(1))

            # Title
            h2 = art.find('h2')
            title = h2.get_text(strip=True) if h2 else ""

            # Content
            p_content = art.find('p', {'data-service-review-text-typography': 'true'})
            content = p_content.get_text(strip=True) if p_content else ""

            # Consumer
            consumer = art.get('data-consumer-name', '')
            if not consumer:
                hd = art.find('aside')
                if hd:
                    consumer = hd.get_text(strip=True)

            # Dates
            time_elem = art.find('time')
            date_pub = time_elem['datetime'] if time_elem and time_elem.has_attr('datetime') else ""

            reviews.append(TrustpilotReview(
                rating=rating,
                title=title,
                content=content,
                consumer_name=consumer,
                date_published=date_pub
            ))

        return reviews, business_info

    def _strip_html_tags(self, text: str) -> str:
        """Supprime les balises HTML (notamment <em> des highlights de recherche)"""
        if not text:
            return ""
        # Supprimer les balises <em> et </em> utilisées pour le highlighting
        clean = re.sub(r'</?em>', '', text)
        # Supprimer toute autre balise HTML potentielle
        clean = re.sub(r'<[^>]+>', '', clean)
        return clean.strip()
