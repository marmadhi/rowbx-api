import unittest
from unittest.mock import MagicMock
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from services.frontend_scraping.category_scraper import PublicCategoryScraper
from services.frontend_scraping.product_scraper import PublicProductScraper
from services.frontend_scraping.provider_scraper import PublicProviderScraper
from services.frontend_scraping.reviews_scraper import PublicReviewsScraper

class TestPublicCategoryScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = PublicCategoryScraper()
        self.scraper.session = MagicMock()

    def test_search_category_parsing(self):
        # Mock JSON response
        data = {
            "products": [
                {"code": "P1", "name": "Prod 1", "price": {"value": 100, "currencyIso": "EUR"}},
                {"code": "P2", "name": "Prod 2"}
            ],
            "pagination": {"totalResults": 2, "currentPage": 0, "pageSize": 16}
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = data
        mock_resp.status_code = 200
        self.scraper.session.get.return_value = mock_resp

        result = self.scraper.search_category("123")
        self.assertEqual(len(result.products), 2)
        self.assertEqual(result.products[0].price, 100)
        self.assertEqual(result.products[1].code, "P2")

class TestPublicProductScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = PublicProductScraper()
        self.scraper.session = MagicMock()

    def test_get_product_activities(self):
        data = {
            "code": "BOX1",
            "sparkowActivities": [
                {"activityName": "Act 1", "id": "A1", "city": "Paris"},
                {"activityName": "Act 2", "id": "A2"}
            ],
            "pagination": {"totalResults": 2}
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = data
        mock_resp.status_code = 200
        self.scraper.session.get.return_value = mock_resp

        result = self.scraper.get_product_activities("BOX1")
        self.assertEqual(len(result.activities), 2)
        self.assertEqual(result.activities[0].city, "Paris")

class TestPublicProviderScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = PublicProviderScraper()
        self.scraper.session = MagicMock()

    def test_parse_partner_html(self):
        html = """
        <html>
            <title>Spa Zen - Paris | Wonderbox</title>
            <script>
                var wbx_gtm_productDetail = true;
                // dimension11: 'wellness'
                // name: 'spa-zen'
            </script>
            <div class="description-col__address">10 Rue de la Paix, 75001 Paris</div>
        </html>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.status_code = 200
        self.scraper.session.get.return_value = mock_resp

        partner = self.scraper.get_partner_details("PART1")
        self.assertEqual(partner.name, "Spa Zen")
        self.assertEqual(partner.city, "Paris") # title parsing
        self.assertEqual(partner.address, "10 Rue de la Paix, 75001 Paris")

if __name__ == '__main__':
    unittest.main()
