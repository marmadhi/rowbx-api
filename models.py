"""
Wonderbox Scraper - Modèles de données
======================================
Dataclasses pour les produits et activités
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


# ============================================================================
# MATÉRIALISATIONS
# ============================================================================

@dataclass
class Materialization:
    """Matérialisation d'un produit (physique, démat, échange)"""
    type: str = ""               # Rematerialisé, Dématerialisé, Échange
    code: str = ""               # FRWOPCSE94R2401N
    ean: str = ""                # 3701066715583
    dlu: str = ""                # "39 mois"
    dlu_type: str = ""           # "glissante"
    available: bool = False


# ============================================================================
# PRODUIT - SOUS-STRUCTURES
# ============================================================================

@dataclass
class ProductImages:
    """URLs des images d'un produit"""
    edito: str = ""
    facing_2d: str = ""
    simul_3d: str = ""
    landscape: str = ""
    lengow: str = ""
    back_card: str = ""
    header: List[str] = field(default_factory=list)
    squared: str = ""


@dataclass
class ProductMerchandising:
    """Données merchandising d'un produit"""
    product_type: str = ""       # Classique, Bundle
    universe: str = ""           # Week-end, Séjour, Bien-être
    pictogram: str = ""          # Exclu web, Nouveau
    thematics: List[str] = field(default_factory=list)
    target_types: List[str] = field(default_factory=list)
    target_ages: List[str] = field(default_factory=list)
    target_numbers: List[str] = field(default_factory=list)


@dataclass
class ProductDescriptions:
    """Descriptions multilingues d'un produit"""
    title: Dict[str, str] = field(default_factory=dict)
    catch_phrase: Dict[str, str] = field(default_factory=dict)
    bullet_points: List[str] = field(default_factory=list)
    short_description: Dict[str, str] = field(default_factory=dict)
    full_description: Dict[str, str] = field(default_factory=dict)
    target_description: Dict[str, str] = field(default_factory=dict)
    program_description: Dict[str, str] = field(default_factory=dict)
    video_link: Dict[str, str] = field(default_factory=dict)
    why_you_will_love: Dict[str, str] = field(default_factory=dict)


@dataclass
class ProductCharacteristics:
    """Caractéristiques d'un produit"""
    tags: List[str] = field(default_factory=list)
    favorite_activities: List[str] = field(default_factory=list)
    weight: str = ""
    durations: List[str] = field(default_factory=list)
    booklet_url_without_addresses: str = ""
    booklet_url_with_addresses: str = ""
    meta_title: Dict[str, str] = field(default_factory=dict)
    meta_keywords: Dict[str, str] = field(default_factory=dict)
    meta_description: Dict[str, str] = field(default_factory=dict)


# ============================================================================
# PRODUIT - DÉTAIL COMPLET
# ============================================================================

@dataclass
class ProductDetail:
    """Détails complets d'un produit"""
    id: int = 0
    code: str = ""
    name: str = ""
    model: str = ""
    collection: str = ""
    version: str = ""
    publisher: str = ""
    status: str = ""
    web_status: str = ""
    price: Optional[float] = None
    descriptions: ProductDescriptions = field(default_factory=ProductDescriptions)
    characteristics: ProductCharacteristics = field(default_factory=ProductCharacteristics)
    merchandising: ProductMerchandising = field(default_factory=ProductMerchandising)
    images: ProductImages = field(default_factory=ProductImages)
    materializations: List[Materialization] = field(default_factory=list)
    ean_codes: List[str] = field(default_factory=list)
    detail_url: str = ""


# ============================================================================
# ACTIVITÉ - SOUS-STRUCTURES
# ============================================================================

@dataclass
class ActivityLocation:
    """Lieu d'une activité"""
    id: int = 0
    name: str = ""
    address: str = ""
    zipcode: str = ""
    city: str = ""
    country: str = ""
    code: str = ""


@dataclass
class ActivityCharacteristics:
    """Caractéristiques d'une activité"""
    duration: str = ""
    weight: str = ""
    room_type: str = ""
    age_brackets: List[str] = field(default_factory=list)
    hotel_service: bool = False
    manual_check_allowed: bool = False
    reservation_required: bool = False
    activity_type: str = ""
    day_moment: str = ""
    meal_moment: str = ""
    family: str = ""
    edition: str = ""
    promo_action: str = ""


@dataclass
class ActivityPricing:
    """Données prix d'une activité"""
    salers: str = ""
    value: Optional[float] = None
    reimbursement: Optional[float] = None
    margin_rate: Optional[float] = None


# ============================================================================
# ACTIVITÉ - DÉTAIL COMPLET
# ============================================================================

@dataclass
class ActivityDetail:
    """Détails complets d'une activité"""
    id: int = 0
    code: str = ""
    name: str = ""
    status: str = ""
    location: ActivityLocation = field(default_factory=ActivityLocation)
    characteristics: ActivityCharacteristics = field(default_factory=ActivityCharacteristics)
    pricing: ActivityPricing = field(default_factory=ActivityPricing)
    price: Optional[float] = None
    price_countries: str = ""
    detail_url: str = ""


# ============================================================================
# ACTIVITÉ - VERSION LISTE
# ============================================================================

@dataclass
class Activity:
    """Activité (version simplifiée pour les listes)"""
    id: int = 0
    code: str = ""
    name: str = ""
    status: str = ""
    activity_type: str = ""
    target: str = ""
    location_name: str = ""
    location_address: str = ""
    location_zipcode: str = ""
    location_city: str = ""
    location_country: str = ""
    location_code: str = ""
    price: Optional[float] = None
    price_currency: str = "EUR"
    price_countries: str = ""
    detail_url: str = ""
    details: Optional[ActivityDetail] = None


# ============================================================================
# PRODUIT - VERSION LISTE
# ============================================================================

@dataclass
class Product:
    """Produit (version liste)"""
    id: int = 0
    code: str = ""
    name: str = ""
    status: str = ""
    product_type: str = ""
    reference: str = ""
    model: str = ""
    publisher: str = ""
    validity_duration: str = ""
    production_year: str = ""
    activities_count: int = 0
    price: Optional[float] = None
    price_currency: str = "EUR"
    price_country: str = ""
    detail_url: str = ""
    activities: Optional[List[Activity]] = None
    details: Optional[ProductDetail] = None
