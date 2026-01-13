import logging
from typing import List, Optional, Callable, Dict
from dataclasses import dataclass, field
from .base_public_scraper import PublicServiceBase
from common.models import PublicProduct

logger = logging.getLogger("PublicCategoryScraper")

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

class PublicCategoryScraper(PublicServiceBase):
    """Scraper pour les pages catégories (recherche produits)"""

    def search_category(
        self,
        category_code: str,
        filters: str = "",
        page: int = 1,
        page_size: int = 16
    ) -> Optional[CategorySearchResult]:
        """Recherche des produits dans une catégorie"""
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

        for p in data.get("products", []):
            product = self._parse_product(p)
            result.products.append(product)

        result.total_products = data.get("pagination", {}).get("totalResults", len(result.products))

        logger.info(f"✅ {len(result.products)} produits trouvés (page {result.current_page + 1})")
        return result

    def get_all_products(
        self,
        category_code: str,
        filters: str = "",
        max_pages: int = None,
        progress_callback: Callable = None
    ) -> List[PublicProduct]:
        """Récupère tous les produits d'une catégorie"""
        self._log_separator(f"SEARCH ALL PAGES {category_code}")

        all_products = []
        page = 1
        total_pages = None

        while True:
            result = self.search_category(category_code, filters, page)

            if not result or not result.products:
                break

            all_products.extend(result.products)

            if total_pages is None and result.total_products:
                total_pages = (result.total_products + result.page_size - 1) // result.page_size

            if progress_callback:
                progress_callback(page, total_pages or page, result.products[-1].code if result.products else "")

            if not result.next_page_url:
                break
            if max_pages and page >= max_pages:
                break

            page += 1

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

        # Prix original
        original_price = data.get("originalPrice", {})
        if original_price:
            product.original_price = original_price.get("value")

        product.discount_percentage = data.get("discountPercentage")

        # Images
        images = data.get("images", [])
        if images:
            product.image_url = images[0].get("url", "")
            product.images = [
                {"url": img.get("url", ""), "format": img.get("format", ""), "type": img.get("imageType", "")}
                for img in images
            ]

        # Categories
        categories = data.get("categories", [])
        product.categories = [c.get("name", "") for c in categories if c.get("name")]
        product.category_codes = [c.get("code", "") for c in categories if c.get("code")]

        # Descriptions
        product.description = data.get("description", "")
        product.short_description = data.get("shortDescription", "")
        product.summary = data.get("summary", "")

        # Caracteristiques
        product.duration = data.get("duration", "")
        product.validity = data.get("validity", "")
        product.universe = data.get("universe", "")

        return product
