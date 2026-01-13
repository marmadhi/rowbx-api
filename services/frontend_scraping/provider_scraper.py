import logging
import re
import json
import html
from typing import Optional, List, Tuple, Dict
from bs4 import BeautifulSoup
from .base_public_scraper import PublicServiceBase
from common.models import PublicPartner, PartnerReview, PartnerActivity

logger = logging.getLogger("PublicProviderScraper")

class PublicProviderScraper(PublicServiceBase):
    """Scraper pour les pages et avis partenaires (frontend)"""

    def get_partner_details(self, partner_code: str) -> Optional[PublicPartner]:
        """Récupère les détails d'un partenaire"""
        self._log_separator(f"PARTNER DETAILS {partner_code}")
        
        url = f"{self.SITE_URL}/l/{partner_code}"
        html_content = self._fetch_html(url)
        
        if not html_content:
            return None

        # Redirection possible
        # Check initial URL vs final url if using requests directly in _fetch_html
        # But here _fetch_html returns text only. 
        # Typically PublicServiceBase should probably return resp so we can check URL? 
        # For simplicity, we assume we got the content. 
        # But if redirect happened, we might want the final URL.
        # Let's adjust if needed. For now parse HTML.

        soup = BeautifulSoup(html_content, 'html.parser')
        
        partner = PublicPartner(
            code=partner_code,
            raw_html=html_content[:5000]
        )
        
        # 1. Title
        title = soup.find('title')
        if title:
            partner.name = title.get_text(strip=True).split(' | ')[0]

        # 2. GTM / Scripts
        for script in soup.find_all('script'):
            if script.string and 'wbx_gtm_productDetail' in script.string:
                match = re.search(r"dimension11:\s*'([^']+)'", script.string)
                if match: partner.category = match.group(1)
                
                match = re.search(r"name:\s*'([^']+)'", script.string)
                if match: partner.slug = match.group(1)
                break

        # 3. Contact
        # Adress
        addr = soup.select_one('.description-col__address') or soup.select_one('.wbx-contact-item--address')
        if addr: partner.address = addr.get_text(strip=True)
        
        # Phone
        phone = soup.select_one('.wbx-contact-item--phone')
        if phone: partner.phone = phone.get_text(strip=True)
        
        # Website
        web = soup.select_one('.wbx-contact-item--link a')
        if web: partner.website = web.get('href', '')

        # 4. Reviews summary
        rating_div = soup.find('div', class_='rating')
        if rating_div:
            try: partner.average_rating = float(rating_div.get('data-rating'))
            except: pass
            
            count = rating_div.find('span', class_='rating__count')
            if count:
                match = re.search(r'(\d+)', count.get_text())
                if match: partner.review_count = int(match.group(1))

        # 5. Activities (GTM)
        divs = soup.find_all('div', class_='show-popin-add', attrs={'data-gtm-box': True})
        for div in divs:
            try:
                data = json.loads(html.unescape(div['data-gtm-box']))
                prods = data.get('ecommerce', {}).get('add', {}).get('products', [])
                for p in prods:
                    act = PartnerActivity(
                        id=p.get('id', ''),
                        name=p.get('name', ''),
                        category=p.get('dimension11', ''),
                        price=float(p.get('price', 0)) if p.get('price') else None
                    )
                    partner.activities.append(act)
            except:
                pass

        # 6. Reviews detailed
        reviews, _, _, _ = self.get_partner_reviews(partner_code)
        partner.reviews = reviews

        return partner

    def get_partner_reviews(self, partner_code: str, max_pages: int = 5) -> Tuple[List[PartnerReview], Optional[float], int, Dict[int, int]]:
        """Récupère les avis"""
        self._log_separator(f"PARTNER REVIEWS {partner_code}")
        
        reviews = []
        url = f"{self.SITE_URL}/p/{partner_code}/reviews"
        html_content = self._fetch_html(url)
        
        if not html_content:
            return [], None, 0, {}
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Parse first page
        reviews.extend(self._parse_reviews_soup(soup))
        
        # Basic pagination logic omitted for brevity, can be added if needed
        # Just simple first page usually enough for MVP or follow structure
        
        return reviews, None, len(reviews), {}

    def _parse_reviews_soup(self, soup) -> List[PartnerReview]:
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
            
            res.append(r)
        return res
