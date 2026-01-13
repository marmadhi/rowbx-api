"""
Configuration et utilitaires communs
====================================
"""
import os
import time
import logging
from functools import wraps
from typing import TypeVar, Callable

logger = logging.getLogger("config")

# ============================================================================
# CONFIGURATION
# ============================================================================

# URLs (peuvent être surchargées par variables d'environnement)
BO_BASE_URL = os.environ.get("WONDERBOX_BO_URL", "http://rowbx2.wonderbox.vpn")
PUBLIC_API_URL = os.environ.get("WONDERBOX_API_URL", "https://www.wonderbox.fr/wonderpublicwebservices/v2/wonderbox-fr/fr")
PUBLIC_SITE_URL = os.environ.get("WONDERBOX_SITE_URL", "https://www.wonderbox.fr")
TRUSTPILOT_URL = os.environ.get("TRUSTPILOT_URL", "https://fr.trustpilot.com")

# Timeouts (en secondes)
DEFAULT_TIMEOUT = 30
QUICKVIEW_TIMEOUT = 10
LOGIN_TIMEOUT = 15

# Rate limiting
REQUEST_DELAY = 0.1  # Délai entre requêtes en secondes

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # Délai initial entre retries (sera multiplié exponentiellement)


# ============================================================================
# DECORATEURS UTILITAIRES
# ============================================================================

T = TypeVar('T')


def retry_on_failure(
    max_retries: int = MAX_RETRIES,
    backoff: float = RETRY_BACKOFF,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Décorateur pour retry automatique avec backoff exponentiel.

    Args:
        max_retries: Nombre maximum de tentatives
        backoff: Délai initial entre retries (sera doublé à chaque retry)
        exceptions: Types d'exceptions à intercepter
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = backoff

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"[RETRY] {func.__name__} attempt {attempt + 1}/{max_retries} "
                            f"failed: {e}. Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= 2  # Backoff exponentiel
                    else:
                        logger.error(
                            f"[RETRY] {func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )

            raise last_exception
        return wrapper
    return decorator


def rate_limited(delay: float = REQUEST_DELAY) -> Callable:
    """
    Décorateur pour limiter le débit des requêtes.

    Args:
        delay: Délai minimum entre les appels (en secondes)
    """
    last_call = [0.0]  # Mutable pour le closure

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            elapsed = time.time() - last_call[0]
            if elapsed < delay:
                time.sleep(delay - elapsed)

            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator
