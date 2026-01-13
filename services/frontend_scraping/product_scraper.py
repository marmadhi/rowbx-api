import logging
from typing import List, Optional, Callable, Dict
from dataclasses import dataclass, field
from .base_public_scraper import PublicServiceBase
from common.models import PublicActivity
import re
from bs4 import BeautifulSoup

logger = logging.getLogger("PublicProductScraper")

@dataclass
class ProductActivitiesResult:
    """Résultat des activités d'un produit"""
    product_code: str = ""
    total_activities: int = 0
    current_page: int = 0
    page_size: int = 8
    activities: List[PublicActivity] = field(default_factory=list)
    facets: List[Dict] = field(default_factory=list)

class PublicProductScraper(PublicServiceBase):
    """Scraper pour les produits (Activités liées)"""

    def get_product_activities(
        self,
        product_code: str,
        filters: str = "",
        page: int = 1,
        page_size: int = 8
    ) -> Optional[ProductActivitiesResult]:
        """Récupère les activités d'un produit"""
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

        # Extraction du slug produit depuis l'URL (ex: /b/spa-en-duo -> spa-en-duo)
        product_url = data.get("url", "")
        product_slug = "common"
        if "/b/" in product_url:
            product_slug = product_url.split("/b/")[-1]
        elif product_url.startswith("/"): 
            product_slug = product_url[1:]

        # Parser les activités
        for a in data.get("sparkowActivities", []):
            activity = self._parse_activity(a)
            # Résolution du partenaire via QuickView
            self._resolve_partner_info(activity, product_code, product_slug)
            result.activities.append(activity)

        result.total_activities = data.get("pagination", {}).get("totalResults", len(result.activities))

        logger.info(f"✅ {len(result.activities)} activités trouvées")
        return result

    def _resolve_partner_info(self, activity: PublicActivity, box_code: str, product_slug: str):
        """Récupère les détails (Code Partenaire) via quickActivityView"""
        try:
            # Construction URL: /{slug}/a/{activity_id}/quickActivityView
            url = f"{self.SITE_URL}/{product_slug}/a/{activity.id}/quickActivityView"
            
            params = {
                "boxCode": box_code,
                "preselect": "box",
                "currentPageUid": "productDetails",
                "activityUrl": f"/{product_slug}/a/{activity.id}",
                # "numberOfReviews": activity.review_count,
                # "averageRating": activity.average_rating
            }
            
            # Headers AJAX
            headers = {'X-Requested-With': 'XMLHttpRequest'}
            
            # Fetch HTML
            resp = self.session.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200:
                logger.debug(f"QuickView echec {resp.status_code} pour {activity.id}")
                return # Fallback or keep empty
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Partner Link -> Code & URL
            # Chercher un lien contenant /l/
            partner_link = soup.find('a', href=re.compile(r'/l/([A-Z0-9]+)'))
            if partner_link:
                href = partner_link.get('href', '')
                activity.partner_url = href
                match = re.search(r'/l/([A-Z0-9]+)', href)
                if match:
                    activity.partner_code = match.group(1)
            
            # 2. Update Description if better one available
            # Note: The popup HTML might contain rich description
            # Looking for typical description classes
            desc_div = soup.select_one('.product-description') or soup.select_one('.description')
            if desc_div:
                text = desc_div.get_text(strip=True)
                if len(text) > len(activity.description):
                    activity.description = text

        except Exception as e:
            logger.debug(f"Erreur QuickView {activity.id}: {e}")

    def get_product_all_activities(
        self,
        product_code: str,
        filters: str = "",
        max_pages: int = None,
        progress_callback: Callable = None
    ) -> List[PublicActivity]:
        """Récupère toutes les activités d'un produit"""
        all_activities = []
        page = 1
        total_pages = None

        while True:
            result = self.get_product_activities(product_code, filters, page)

            if not result or not result.activities:
                break

            all_activities.extend(result.activities)

            if total_pages is None and result.total_activities:
                total_pages = (result.total_activities + result.page_size - 1) // result.page_size

            if progress_callback:
                progress_callback(page, total_pages or page, result.activities[-1].name[:30] if result.activities else "")

            if len(result.activities) < result.page_size:
                break
            if max_pages and page >= max_pages:
                break

            page += 1

        return all_activities

    def _parse_activity(self, data: Dict) -> PublicActivity:
        """Parse une activité depuis le JSON"""
        activity_id = data.get("activityId") or data.get("id") or data.get("code") or ""
        
        # Coordonnées et Location (via pointOfService)
        point_of_service = data.get("pointOfService", {})
        address = point_of_service.get("address", {})
        
        lat = point_of_service.get("latitude") or data.get("latitude") or data.get("lat")
        lon = point_of_service.get("longitude") or data.get("longitude") or data.get("lon")
        
        city = address.get("town") or data.get("city") or data.get("locationCity") or ""
        country = address.get("country", {}).get("name") or data.get("country") or ""
        region = ""
        if point_of_service.get("departments"):
            region = point_of_service.get("departments")[0]
        elif point_of_service.get("region", {}).get("name"):
            region = point_of_service.get("region", {}).get("name")
        else:
            region = data.get("parentRegion") or data.get("region") or ""

        images = data.get("images", [])
        image_url = images[0].get("url", "") if images else ""

        return PublicActivity(
            id=str(activity_id),
            name=data.get("activityTitle") or data.get("title") or data.get("activityName") or data.get("name") or "",
            partner_name=data.get("partnerName") or data.get("partnerCompanyName") or "",
            city=city,
            region=region,
            country=country,
            average_rating=data.get("activityCustomerAverageRating") or data.get("averageRating"),
            review_count=int(data.get("activityCustomerReviewQuantity") or data.get("numberOfReviews") or 0),
            description=data.get("programDescription") or data.get("shortDescription") or "",
            
            # Champs enrichis
            price=float(data.get("price", {}).get("value") or 0.0),
            currency=data.get("price", {}).get("currencyIso", "EUR"),
            universe=data.get("universe", ""),
            is_favorite=data.get("favorite", False),
            participants=data.get("targetDescription", ""),
            duration_text=data.get("programDescription", ""),
            
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            image_url=image_url,
            raw_data=data
        )
