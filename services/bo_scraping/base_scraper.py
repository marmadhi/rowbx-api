import requests
import logging
import re
from typing import Optional, Dict, Tuple, List

# Logger
logger = logging.getLogger("BOScraper")

class BOServiceBase:
    BASE_URL = "http://rowbx2.wonderbox.vpn"
    
    def __init__(self, cookies: Dict[str, str] = None, session: requests.Session = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        })
        if cookies:
            self.session.cookies.update(cookies)
    
    def _log_separator(self, title: str = ""):
        """Affiche un séparateur dans les logs"""
        if title:
            logger.info("=" * 60)
            logger.info(f"  {title}")
            logger.info("=" * 60)
    
    def _fetch_page(self, url: str, description: str = "") -> Optional[str]:
        """Récupère une page avec logging"""
        logger.debug(f"[FETCH] {description}")
        
        try:
            resp = self.session.get(url, timeout=30)
            
            if resp.status_code != 200:
                logger.error(f"[FETCH] ❌ Erreur HTTP {resp.status_code}")
                return None
            
            # Vérifier si redirection vers login
            if 'auth/login' in resp.url:
                logger.error(f"[FETCH] ❌ Redirection vers login détectée!")
                return None
            
            # Vérifier le contenu pour détecter une page de login cachée
            if 'name="username"' in resp.text and 'name="password"' in resp.text:
                logger.error(f"[FETCH] ❌ Page de login détectée dans le contenu!")
                return None
            
            return resp.text
            
        except Exception as e:
            logger.error(f"[FETCH] ❌ Exception: {e}")
            return None
    
    def login(self, username: str, password: str) -> bool:
        """Connexion au site via l'API JSON"""
        self._log_separator("LOGIN")
        login_url = f"{self.BASE_URL}/json/auth/adminauth"

        try:
            data = {'login': username, 'password': password}
            resp = self.session.post(login_url, data=data, allow_redirects=True)

            if resp.status_code == 200:
                is_connected, msg = self.test_connection()
                if is_connected:
                    logger.info(f"Login: ✅ Succès - {msg}")
                    return True

            logger.warning("Login: ❌ Échec")
            return False
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def _build_filter_url_parts(self, filters: Dict) -> List[str]:
        """Construit les segments d'URL à partir des filtres (Helper générique)"""
        parts = []
        for key, value in filters.items():
            if value is None or value == "": continue
                
            # Handle Lists (Checkbox arrays)
            if isinstance(value, list):
                clean_values = [str(v) for v in value if v]
                if clean_values:
                    parts.append(f"{key}/{','.join(clean_values)}")
            
            # Handle Booleans
            elif isinstance(value, bool):
                parts.append(f"{key}/{'1' if value else '0'}")
                
            # Handle Simple Values
            else:
                parts.append(f"{key}/{value}")
                
        return parts

    def test_connection(self) -> Tuple[bool, str]:
        """Teste la connexion"""
        try:
            resp = self.session.get(f"{self.BASE_URL}/search/box", timeout=10)
            
            if resp.status_code == 200:
                if 'auth' in resp.url.lower() and 'login' in resp.url.lower():
                    return False, "Session expirée"
                
                if 'name="username"' in resp.text and 'name="password"' in resp.text:
                    return False, "Session expirée"
                
                if 'logout' in resp.text.lower():
                    match = re.search(r'info-login-name[^>]*>([^<]+)<', resp.text)
                    username = match.group(1).strip() if match else "inconnu"
                    return True, f"Connecté ({username})"
                
                if 'box-result' in resp.text or 'search/box' in resp.text:
                    return True, "Page accessible"
                
                return False, "Session invalide"
            
            return False, f"Erreur HTTP {resp.status_code}"
            
        except Exception as e:
            return False, str(e)
