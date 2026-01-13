import logging
import re
from typing import Optional, Dict
from bs4 import BeautifulSoup
from .base_public_scraper import PublicServiceBase
from .provider_scraper import PublicProviderScraper
# Reuse provider scraper to get logic if needed, or implement standalone

logger = logging.getLogger("PublicActivityScraper")

class PublicActivityScraper(PublicServiceBase):
    """Scraper pour les détails activité (redirection vers partenaire)"""
    
    def get_activity_details(self, activity_code: str) -> Optional[Dict]:
        """Récupère les détails via redirection /a/{code} et scraping page partenaire"""
        self._log_separator(f"ACTIVITY DETAILS {activity_code}")
        
        url = f"{self.SITE_URL}/a/{activity_code}"
        try:
            # 1. Resolve URL to get Partner Code
            resp = self.session.head(url, allow_redirects=True, timeout=10)
            final_url = resp.url
            
            partner_code_match = re.search(r'/l/([A-Z0-9]+)', final_url)
            partner_code = partner_code_match.group(1) if partner_code_match else ""
            
            result = {
                "activity_code": activity_code,
                "partner_code": partner_code,
                "partner_url": final_url,
                "activity_data": None,
                "partner_data": None
            }
            
            if partner_code:
                # 2. Use ProviderScraper to get full details
                provider_scraper = PublicProviderScraper()
                # We can inject session if needed, but new instance is fine
                partner = provider_scraper.get_partner_details(partner_code)
                
                if partner:
                    result["partner_data"] = {
                        "name": partner.name,
                        "address": partner.address,
                        "description": partner.description,
                        "rating": partner.average_rating,
                        "url": partner.url
                    }
                    
                    # 3. Find specific activity in partner's activities
                    target_act = next((a for a in partner.activities if a.id == activity_code), None)
                    if target_act:
                        result["activity_data"] = {
                            "name": target_act.name,
                            "price": target_act.price,
                            "category": target_act.category
                        }
                    else:
                        # Fallback: Scrape activity from raw HTML if not in GTM?
                        # Or just return whatever we have
                        pass
                        
            return result

        except Exception as e:
            logger.error(f"Error scraping activity {activity_code}: {e}")
            return None
