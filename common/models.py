"""
Wonderbox Scraper - Modèles de données
======================================
Dataclasses pour les produits et activités
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


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
    phone: str = ""
    email: str = ""
    website: str = ""
    latitude: str = ""
    longitude: str = ""
    region: str = ""
    department: str = ""


@dataclass
class ActivityDescriptions:
    """Descriptions multilingues d'une activité"""
    name: Dict[str, str] = field(default_factory=dict)
    description: Dict[str, str] = field(default_factory=dict)
    short_description: Dict[str, str] = field(default_factory=dict)
    conditions: Dict[str, str] = field(default_factory=dict)
    practical_info: Dict[str, str] = field(default_factory=dict)
    included: Dict[str, str] = field(default_factory=dict)
    not_included: Dict[str, str] = field(default_factory=dict)
    highlights: Dict[str, str] = field(default_factory=dict)


@dataclass
class ActivityCharacteristics:
    """Caractéristiques d'une activité"""
    duration: str = ""
    duration_unit: str = ""
    weight: str = ""
    room_type: str = ""
    age_brackets: List[str] = field(default_factory=list)
    hotel_service: bool = False
    manual_check_allowed: bool = False
    reservation_required: bool = False
    activity_type: str = ""
    activity_subtype: str = ""
    day_moment: str = ""
    meal_moment: str = ""
    family: str = ""
    edition: str = ""
    promo_action: str = ""
    # Nouveaux champs
    capacity_min: int = 0
    capacity_max: int = 0
    nb_persons: str = ""
    validity_days: str = ""
    booking_delay: str = ""
    cancellation_policy: str = ""
    seasons: List[str] = field(default_factory=list)
    days_available: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    accessibility: List[str] = field(default_factory=list)
    equipment_provided: List[str] = field(default_factory=list)
    equipment_required: List[str] = field(default_factory=list)


@dataclass
class ActivityPricing:
    """Données prix d'une activité"""
    salers: str = ""
    value: Optional[float] = None
    value_currency: str = "EUR"
    reimbursement: Optional[float] = None
    margin_rate: Optional[float] = None
    commission: Optional[float] = None
    commission_rate: Optional[float] = None
    partner_price: Optional[float] = None
    public_price: Optional[float] = None
    prices_by_country: Dict[str, float] = field(default_factory=dict)


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
    web_status: str = ""
    publisher: str = ""
    target: str = ""
    location: ActivityLocation = field(default_factory=ActivityLocation)
    descriptions: ActivityDescriptions = field(default_factory=ActivityDescriptions)
    characteristics: ActivityCharacteristics = field(default_factory=ActivityCharacteristics)
    pricing: ActivityPricing = field(default_factory=ActivityPricing)
    price: Optional[float] = None
    price_countries: str = ""
    detail_url: str = ""
    images: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)  # Codes des coffrets associés
    partner_name: str = ""
    partner_code: str = ""
    created_at: str = ""
    updated_at: str = ""


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
    web_status: str = ""
    activity_type: str = ""
    activity_subtype: str = ""
    target: str = ""
    publisher: str = ""
    # Location
    location_id: int = 0
    location_name: str = ""
    location_address: str = ""
    location_zipcode: str = ""
    location_city: str = ""
    location_country: str = ""
    location_code: str = ""
    location_region: str = ""
    location_department: str = ""
    # Prix
    price: Optional[float] = None
    price_currency: str = "EUR"
    price_countries: str = ""
    partner_price: Optional[float] = None
    margin_rate: Optional[float] = None
    # Caractéristiques de liste
    duration: str = ""
    weight: str = ""
    nb_persons: str = ""
    partner_name: str = ""
    partner_code: str = ""
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
    web_status: str = ""
    product_type: str = ""
    reference: str = ""
    model: str = ""
    collection: str = ""
    version: str = ""
    publisher: str = ""
    validity_duration: str = ""
    production_year: str = ""
    activities_count: int = 0
    # Prix
    price: Optional[float] = None
    price_currency: str = "EUR"
    price_country: str = ""
    prices_by_country: Dict[str, float] = field(default_factory=dict)
    # Métadonnées supplémentaires de liste
    universe: str = ""
    pictogram: str = ""
    thematics: List[str] = field(default_factory=list)
    ean_code: str = ""
    detail_url: str = ""
    activities: Optional[List[Activity]] = None
    details: Optional[ProductDetail] = None


# ============================================================================
# API PUBLIQUE - MODÈLES
# ============================================================================

@dataclass
class PublicProduct:
    """Produit depuis l'API publique wonderbox.fr"""
    code: str = ""
    name: str = ""
    url: str = ""
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[int] = None
    currency: str = "EUR"
    image_url: str = ""
    images: List[Dict[str, str]] = field(default_factory=list)
    activity_count: int = 0
    average_rating: Optional[float] = None
    review_count: int = 0
    bookable_online: bool = False
    categories: List[str] = field(default_factory=list)
    category_codes: List[str] = field(default_factory=list)
    description: str = ""
    short_description: str = ""
    summary: str = ""
    duration: str = ""
    validity: str = ""
    universe: str = ""
    thematics: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    meta_title: str = ""
    meta_description: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PartnerReview:
    """Avis client d'un partenaire"""
    id: str = ""
    title: str = ""
    comment: str = ""
    rating: int = 0
    username: str = ""
    date: str = ""
    experience_date: str = ""
    activity_code: str = ""
    activity_name: str = ""
    helpful_count: int = 0


@dataclass
class PartnerActivity:
    """Activité extraite de la page partenaire"""
    id: str = ""
    name: str = ""
    theme: str = ""
    subtheme: str = ""
    category: str = ""
    price: Optional[float] = None
    price_discount: Optional[float] = None
    department: str = ""
    type: str = ""


@dataclass
class PublicPartner:
    """Partenaire depuis le site wonderbox.fr"""
    code: str = ""
    name: str = ""
    slug: str = ""
    url: str = ""
    theme: str = ""
    subtheme: str = ""
    category: str = ""
    address: str = ""
    city: str = ""
    zipcode: str = ""
    region: str = ""
    department: str = ""
    country: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: str = ""
    email: str = ""
    website: str = ""
    description: str = ""
    highlights: List[str] = field(default_factory=list)
    included: List[str] = field(default_factory=list)
    practical_info: str = ""
    images: List[str] = field(default_factory=list)
    average_rating: Optional[float] = None
    review_count: int = 0
    rating_distribution: Dict[int, int] = field(default_factory=dict)
    reviews: List[PartnerReview] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    activities: List[PartnerActivity] = field(default_factory=list)
    raw_html: str = ""


@dataclass
class PublicActivity:
    """Activité depuis l'API publique wonderbox.fr"""
    id: str = ""
    name: str = ""
    partner_name: str = ""
    partner_code: str = ""
    partner_url: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    address: str = ""
    zipcode: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    average_rating: Optional[float] = None
    review_count: int = 0
    image_url: str = ""
    description: str = ""
    theme: str = ""
    
    # Nouveaux champs enrichis
    price: Optional[float] = None
    currency: str = ""
    universe: str = ""
    is_favorite: bool = False
    participants: str = ""
    duration_text: str = ""
    
    raw_data: Dict[str, Any] = field(default_factory=dict)




# ============================================================================
# PARTENAIRE
# ============================================================================

@dataclass
class Partner:
    """Partenaire (version liste)"""
    id: int = 0
    code: str = ""
    name: str = ""
    status: str = ""
    web_status: str = ""
    publisher: str = ""
    detail_url: str = ""
    address: str = ""
    zipcode: str = ""
    city: str = ""
    country: str = ""


@dataclass
class PartnerDetail:
    """Détails complets d'un partenaire"""
    id: int = 0
    code: str = ""
    name: str = ""
    status: str = ""
    web_status: str = ""
    publisher: str = ""
    detail_url: str = ""
    # Coordonnées
    address: str = ""
    zipcode: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    # Metadonnées
    rating: Optional[float] = None
    reviews_count: int = 0
    activities_count: int = 0


# ============================================================================
# TRUSTPILOT
# ============================================================================

@dataclass
class TrustpilotReview:
    """Avis Trustpilot"""
    id: str = ""
    consumer_name: str = ""
    rating: int = 0
    title: str = ""
    content: str = ""
    date_published: str = ""
    date_experienced: str = ""
    reply_content: str = ""
    reply_date: str = ""
    url: str = ""
    likes: int = 0



