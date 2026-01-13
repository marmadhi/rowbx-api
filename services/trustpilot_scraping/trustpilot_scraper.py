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
        
    def get_reviews(self, domain: str, pages: int = 1, stars: List[int] = None) -> List[TrustpilotReview]:
        """Récupère les avis pour un domaine"""
        all_reviews = []
        
        # Filtrage par étoiles via l'URL ?stars=4,5
        params = {}
        if stars:
            params['stars'] = ",".join(map(str, stars))
            
        for page in range(1, pages + 1):
            url = f"{self.BASE_URL}/review/{domain}"
            current_params = params.copy()
            if page > 1:
                current_params['page'] = page
                
            try:
                logger.info(f"Scraping Trustpilot {domain} page {page}")
                resp = self.session.get(url, params=current_params, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Stop: HTTP {resp.status_code}")
                    break
                    
                reviews = self._parse_reviews_page(resp.text)
                if not reviews:
                    break
                    
                all_reviews.extend(reviews)
                
            except Exception as e:
                logger.error(f"Erreur scraping: {e}")
                break
                
        return all_reviews
        
    def _parse_reviews_page(self, html: str) -> List[TrustpilotReview]:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Essayer via JSON-LD ou NextJS data si disponible
        # Trustpilot change souvent, HTML parsing classique est risqué mais on tente
        
        # Next Data script
        reviews = []
        
        # Approche 1: Next.js DATA
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            try:
                data = json.loads(script.string)
                props = data.get('props', {}).get('pageProps', {})
                reviews_data = props.get('reviews', [])
                
                for r in reviews_data:
                    review = TrustpilotReview(
                        id=r.get('id', ''),
                        consumer_name=r.get('consumer', {}).get('displayName', ''),
                        rating=r.get('rating', 0),
                        title=r.get('title', ''),
                        content=r.get('text', ''),
                        date_published=r.get('dates', {}).get('publishedDate', ''),
                        date_experienced=r.get('dates', {}).get('experiencedDate', ''),
                    )
                    
                    if r.get('reply'):
                        review.reply_content = r['reply'].get('message', '')
                        review.reply_date = r['reply'].get('publishedDate', '')
                        
                    reviews.append(review)
                
                if reviews:
                    return reviews
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Parse error: {e}")
                
        # Approche 2: HTML classes (Fallback)
        # Classes: styles_cardWrapper__..., styles_reviewContent__...
        # C'est fragile car hash dans les classes.
        # On peut chercher par article
        
        articles = soup.find_all('article')
        for art in articles:
            # Rating
            star_img = art.find('img', alt=re.compile(r'Note : \d'))
            rating = 0
            if star_img:
                match = re.search(r'Note : (\d)', star_img['alt'])
                if match: rating = int(match.group(1))
            
            # Title
            h2 = art.find('h2')
            title = h2.get_text(strip=True) if h2 else ""
            
            # Content
            p_content = art.find('p', {'data-service-review-text-typography': 'true'})
            content = p_content.get_text(strip=True) if p_content else ""
            
            # Consumer
            consumer = art.get('data-consumer-name', '') # Parfois pas dispo direct, à chercher dans header
            if not consumer:
                hd = art.find('aside')
                if hd: consumer = hd.get_text(strip=True)

            # Dates
            time_elem = art.find('time')
            date_pub = time_elem['datetime'] if time_elem else ""
            
            reviews.append(TrustpilotReview(
                rating=rating,
                title=title,
                content=content,
                consumer_name=consumer,
                date_published=date_pub
            ))
            
        return reviews
