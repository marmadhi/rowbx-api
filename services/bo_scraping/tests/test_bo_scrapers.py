import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Ajouter le dossier racine au path pour les imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from services.bo_scraping.box_scraper import BOBoxScraper
from services.bo_scraping.activity_scraper import BOActivityScraper
from services.bo_scraping.provider_scraper import BOProviderScraper
from common.models import ProductDetail, ActivityDetail

class TestBOBoxScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = BOBoxScraper()
        # Mock session to avoid network calls
        self.scraper.session = MagicMock()

    def test_parse_product_row(self):
        # HTML simulé d'une ligne produit
        html = """
        <tr class="bg-light">
            <td></td>
            <td><input type="checkbox" ng-model="check123"></td>
            <td><a href="/box/index/id/123">B33O01</a>|ACTIVE</td>
            <td><a href="/box/index/id/123">Coffret Test</a>|Classique|Ref123</td>
            <td>ACTIVE</td>
            <td>ModelX</td>
            <td>Collection/Version</td>
            <td>FRANCE</td>
            <td>39 mois</td>
            <td>2024</td>
            <td>10 prestations</td>
            <td>49.90 € (FR)</td>
        </tr>
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')
        
        product = self.scraper._parse_product_row(row)
        
        self.assertIsNotNone(product)
        self.assertEqual(product.id, 123)
        self.assertEqual(product.code, "B33O01")
        self.assertEqual(product.web_status, "ACTIVE")
        self.assertEqual(product.price, 49.9)

class TestBOActivityScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = BOActivityScraper()
        self.scraper.session = MagicMock()

    def test_parse_activity_presentation(self):
        html = """
        <html>
            <h1>Activity Name</h1>
            <a href="/activity/index/id/555">A12345</a>
            <select name="status"><option selected>active</option></select>
            <input name="address" value="123 Rue de Test">
        </html>
        """
        detail = self.scraper._parse_activity_presentation(html, 555)
        self.assertEqual(detail.id, 555)
        self.assertEqual(detail.name, "Activity Name")
        self.assertEqual(detail.code, "A12345")
        self.assertEqual(detail.status, "active")
        self.assertEqual(detail.location.address, "123 Rue de Test")

if __name__ == '__main__':
    unittest.main()
