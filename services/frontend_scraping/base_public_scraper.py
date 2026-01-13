import logging
import requests
from typing import Optional, Dict
from requests.exceptions import RequestException, Timeout, ConnectionError

from common.config import (
    PUBLIC_API_URL, PUBLIC_SITE_URL, DEFAULT_TIMEOUT,
    retry_on_failure, MAX_RETRIES
)

logger = logging.getLogger("PublicServiceBase")


class PublicServiceBase:
    """Base pour les services de scraping public"""

    BASE_URL = PUBLIC_API_URL
    SITE_URL = PUBLIC_SITE_URL

    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        })

    def _log_separator(self, title: str):
        logger.info(f"{'='*20} {title} {'='*20}")

    @retry_on_failure(max_retries=MAX_RETRIES, exceptions=(RequestException, Timeout, ConnectionError))
    def _fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Récupère du JSON depuis l'API avec retry automatique"""
        logger.debug(f"[FETCH] GET {url}")
        if params:
            logger.debug(f"[FETCH] Params: {params}")

        resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()

        data = resp.json()
        return data

    @retry_on_failure(max_retries=MAX_RETRIES, exceptions=(RequestException, Timeout, ConnectionError))
    def _fetch_html(self, url: str) -> Optional[str]:
        """Récupère le HTML d'une page publique avec retry automatique"""
        logger.debug(f"[FETCH] GET HTML {url}")
        resp = self.session.get(url, headers={'Accept': 'text/html'}, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.text
