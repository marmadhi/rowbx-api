import unittest
from unittest.mock import MagicMock
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from services.trustpilot_scraping.trustpilot_scraper import TrustpilotScraper

class TestTrustpilotScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = TrustpilotScraper()
        self.scraper.session = MagicMock()

    def test_parse_reviews_next_data(self):
        # Simulation d'un json Next.js
        json_data = {
            "props": {
                "pageProps": {
                    "reviews": [
                        {
                            "id": "R1",
                            "consumer": {"displayName": "User1"},
                            "rating": 5,
                            "title": "Great",
                            "text": "Excellent service",
                            "dates": {"publishedDate": "2024-01-01"}
                        }
                    ]
                }
            }
        }
        import json
        html = f"""
        <html>
            <script id="__NEXT_DATA__" type="application/json">{json.dumps(json_data)}</script>
        </html>
        """
        
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.status_code = 200
        self.scraper.session.get.return_value = mock_resp
        
        reviews = self.scraper.get_reviews("example.com")
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].rating, 5)
        self.assertEqual(reviews[0].content, "Excellent service")

if __name__ == '__main__':
    unittest.main()
