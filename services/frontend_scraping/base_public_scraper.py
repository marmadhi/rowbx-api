import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger("PublicServiceBase")

class PublicServiceBase:
    """Base pour les services de scraping public"""
    
    BASE_URL = "https://www.wonderbox.fr/wonderpublicwebservices/v2/wonderbox-fr/fr"
    SITE_URL = "https://www.wonderbox.fr"
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        })
        
    def _log_separator(self, title: str):
        logger.info(f"{'='*20} {title} {'='*20}")
        
    def _fetch_json(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Récupère du JSON depuis l'API"""
        try:
            logger.debug(f"[FETCH] GET {url}")
            if params:
                logger.debug(f"[FETCH] Params: {params}")
                
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            # logger.debug(f"[FETCH] ✅ {len(str(data))} chars")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[FETCH] ❌ Erreur Request: {e}")
            return None
        except ValueError as e:
            logger.error(f"[FETCH] ❌ JSON invalide: {e}")
            return None
            
    def _fetch_html(self, url: str) -> Optional[str]:
        """Récupère le HTML d'une page publique"""
        try:
            logger.debug(f"[FETCH] GET HTML {url}")
            resp = self.session.get(url, headers={'Accept': 'text/html'}, timeout=30)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"[FETCH] ❌ Erreur HTML: {e}")
            return None
