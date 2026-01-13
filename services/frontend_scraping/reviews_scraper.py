import logging
import re
from typing import List, Tuple, Optional, Dict
from bs4 import BeautifulSoup
from .base_public_scraper import PublicServiceBase
from common.models import PartnerReview

logger = logging.getLogger("PublicReviewsScraper")

class PublicReviewsScraper(PublicServiceBase):
    """Scraper pour les avis partenaires"""
    
    def get_reviews(self, partner_code: str, max_pages: int = 5) -> Tuple[List[PartnerReview], Optional[float], int]:
        """Récupère les avis d'un partenaire"""
        self._log_separator(f"REVIEWS {partner_code}")
        
        reviews = []
        url = f"{self.SITE_URL}/p/{partner_code}/reviews"
        
        html = self._fetch_html(url)
        if not html:
            return [], None, 0
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Stats
        avg = None
        total = 0
        
        total_input = soup.select_one('input.totalNumberOfReviews')
        if total_input:
            try: total = int(total_input.get('value', 0))
            except (ValueError, TypeError):
                    pass
            
        avg_elem = soup.select_one('.reviews-avg')
        if avg_elem:
            match = re.search(r'([\d,]+)/5', avg_elem.get_text())
            if match:
                try: avg = float(match.group(1).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
                
        # Reviews Page 1
        reviews.extend(self._parse_reviews(soup))
        
        # Simple Loop for pages
        page = 2
        while len(reviews) < total and page <= max_pages:
            next_url = f"{url}?page={page*10}" # Offset 10
            next_html = self._fetch_html(next_url)
            if not next_html: break
            
            next_soup = BeautifulSoup(next_html, 'html.parser')
            new_reviews = self._parse_reviews(next_soup)
            if not new_reviews: break
            
            reviews.extend(new_reviews)
            page += 1
            
        return reviews, avg, total

    def _parse_reviews(self, soup) -> List[PartnerReview]:
        res = []
        for comment in soup.select('.wbx-comment'):
            r = PartnerReview()
            stars = comment.select('.review-rating .icon-nsw-star.full')
            r.rating = len(stars)
            
            title = comment.select_one('.review-title')
            if title: r.title = title.get_text(strip=True)
            
            body = comment.select_one('.review-comment')
            if body: r.comment = body.get_text(strip=True)
            
            user = comment.select_one('.review-username--name')
            if user: r.username = user.get_text(strip=True)
            
            date = comment.select_one('.review-date--date')
            if date: r.date = date.get_text(strip=True)
            
            act_link = comment.select_one('.review-link a')
            if act_link:
                r.activity_name = act_link.get('title', '')
                try:
                    match = re.search(r'/a/([A-Z0-9]+)', act_link['href'])
                    if match: r.activity_code = match.group(1)
                except (ValueError, TypeError):
                    pass
            
            res.append(r)
        return res
