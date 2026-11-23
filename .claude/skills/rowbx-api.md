# Wonderbox Rowbx Scraper API

Documentation de l'API du scraper pour le back-office Rowbx/Wonderbox.

## Configuration

### Authentification
- **URL Base**: `http://rowbx2.wonderbox.vpn` (requiert VPN)
- **Méthode**: Cookie `PHPSESSID` ou login/password
- **Récupérer le cookie**: F12 > Application > Cookies > PHPSESSID

### Instanciation
```python
from scraper import WonderboxScraper

# Avec cookie
scraper = WonderboxScraper(cookies={'PHPSESSID': 'votre_cookie'})

# Avec login
scraper = WonderboxScraper()
scraper.login('username', 'password')

# Test connexion
success, message = scraper.test_connection()
```

---

## Endpoints Produits

### Recherche de produits
```python
# Recherche paginée
products, total, total_pages = scraper.search_products(
    publisher="FRANCE",      # FRANCE, BELGIUM, SPAIN, ITALY
    web_status="ACTIVE",     # ACTIVE, ARCHIVED, PUBLISHABLE
    page=1
)

# Tous les produits
products = scraper.get_all_products(
    publisher="FRANCE",
    web_status="ACTIVE",
    max_pages=10,            # None = tout
    progress_callback=fn     # fn(page, total_pages, count, total)
)
```

### Détails d'un produit
```python
detail = scraper.get_product_detail(
    product_id=32953,
    fetch_all_tabs=True      # Charge les 3 onglets
)
```

### Produits avec détails complets
```python
products = scraper.get_all_products_with_details(
    publisher="FRANCE",
    web_status="ACTIVE",
    max_pages=5,
    include_activities=True,
    include_activity_details=True,
    progress_callback=fn
)
```

### Recherche par pays
```python
# Par pays de prix
products, total, pages = scraper.search_products_by_country(
    country="FR",            # FR, BE, ES, IT, PT, NL, CH, LU
    publisher="FRANCE",
    web_status="ACTIVE",
    page=1
)

products = scraper.get_all_products_by_country(
    country="FR",
    publisher="FRANCE",
    web_status="ACTIVE",
    max_pages=10,
    include_details=True
)
```

---

## Endpoints Activités

### Recherche d'activités par produit
```python
activities, total, pages = scraper.search_activities(
    box_code="FRWOPCSE94",   # Code du coffret
    publisher="FRANCE",
    web_status="ACTIVE",
    page=1
)

activities = scraper.get_all_activities_for_product(
    box_code="FRWOPCSE94",
    publisher="FRANCE",
    web_status="ACTIVE"
)
```

### Détails d'une activité
```python
detail = scraper.get_activity_detail(
    activity_id=529215,
    fetch_all_tabs=True
)
```

### Recherche par pays (localisation)
```python
activities, total, pages = scraper.search_activities_by_country(
    country="FR",
    publisher="FRANCE",
    web_status="ACTIVE",
    page=1
)

activities = scraper.get_all_activities_by_country(
    country="FR",
    publisher="FRANCE",
    web_status="ACTIVE",
    max_pages=10
)
```

---

## Modèles de données

### Product (liste)
```python
@dataclass
class Product:
    id: int
    code: str                    # FRWOPCSE94
    name: str
    status: str
    web_status: str
    product_type: str            # Classique, Bundle
    reference: str
    model: str                   # SE94
    collection: str
    version: str
    publisher: str               # FRANCE, BELGIUM...
    validity_duration: str
    production_year: str
    activities_count: int
    price: float
    price_currency: str          # EUR
    price_country: str           # FR
    prices_by_country: Dict[str, float]
    universe: str
    pictogram: str
    thematics: List[str]
    ean_code: str
    detail_url: str
    activities: List[Activity]
    details: ProductDetail
```

### ProductDetail (complet)
```python
@dataclass
class ProductDetail:
    id: int
    code: str
    name: str
    model: str
    collection: str
    version: str
    publisher: str
    status: str
    web_status: str
    price: float
    descriptions: ProductDescriptions
    characteristics: ProductCharacteristics
    merchandising: ProductMerchandising
    images: ProductImages
    materializations: List[Materialization]
    ean_codes: List[str]
    detail_url: str
```

### ProductDescriptions
```python
@dataclass
class ProductDescriptions:
    title: Dict[str, str]              # {'fr': '...', 'en': '...'}
    catch_phrase: Dict[str, str]
    bullet_points: List[str]
    short_description: Dict[str, str]
    full_description: Dict[str, str]
    target_description: Dict[str, str]
    program_description: Dict[str, str]
    video_link: Dict[str, str]
    why_you_will_love: Dict[str, str]
```

### ProductCharacteristics
```python
@dataclass
class ProductCharacteristics:
    tags: List[str]
    favorite_activities: List[str]
    weight: str
    durations: List[str]               # ['1', '2'] = 1 ou 2 nuits
    booklet_url_without_addresses: str
    booklet_url_with_addresses: str
    meta_title: Dict[str, str]
    meta_keywords: Dict[str, str]
    meta_description: Dict[str, str]
```

### ProductMerchandising
```python
@dataclass
class ProductMerchandising:
    product_type: str           # Classique, Bundle
    universe: str               # Week-end, Séjour, Bien-être
    pictogram: str              # Exclu web, Nouveau
    thematics: List[str]
    target_types: List[str]
    target_ages: List[str]
    target_numbers: List[str]
```

### ProductImages
```python
@dataclass
class ProductImages:
    edito: str
    facing_2d: str
    simul_3d: str
    landscape: str
    lengow: str
    back_card: str
    header: List[str]
    squared: str
```

### Materialization
```python
@dataclass
class Materialization:
    type: str           # Rematerialisé, Dématerialisé, Échange
    code: str           # FRWOPCSE94R2401N
    ean: str            # 3701066715583
    dlu: str            # "39 mois"
    dlu_type: str       # "glissante" ou "fixe"
    available: bool
```

### Activity (liste)
```python
@dataclass
class Activity:
    id: int
    code: str
    name: str
    status: str
    web_status: str
    activity_type: str
    activity_subtype: str
    target: str
    publisher: str
    location_id: int
    location_name: str
    location_address: str
    location_zipcode: str
    location_city: str
    location_country: str
    location_code: str
    location_region: str
    location_department: str
    price: float
    price_currency: str
    price_countries: str
    partner_price: float
    margin_rate: float
    duration: str
    weight: str
    nb_persons: str
    partner_name: str
    partner_code: str
    detail_url: str
    details: ActivityDetail
```

### ActivityDetail (complet)
```python
@dataclass
class ActivityDetail:
    id: int
    code: str
    name: str
    status: str
    web_status: str
    publisher: str
    target: str
    location: ActivityLocation
    descriptions: ActivityDescriptions
    characteristics: ActivityCharacteristics
    pricing: ActivityPricing
    price: float
    price_countries: str
    detail_url: str
    images: List[str]
    products: List[str]        # Codes coffrets associés
    partner_name: str
    partner_code: str
    created_at: str
    updated_at: str
```

### ActivityLocation
```python
@dataclass
class ActivityLocation:
    id: int
    name: str
    address: str
    zipcode: str
    city: str
    country: str
    code: str
    phone: str
    email: str
    website: str
    latitude: str
    longitude: str
    region: str
    department: str
```

### ActivityCharacteristics
```python
@dataclass
class ActivityCharacteristics:
    duration: str
    duration_unit: str
    weight: str
    room_type: str
    age_brackets: List[str]
    hotel_service: bool
    manual_check_allowed: bool
    reservation_required: bool
    activity_type: str
    activity_subtype: str
    day_moment: str
    meal_moment: str
    family: str
    edition: str
    promo_action: str
    capacity_min: int
    capacity_max: int
    nb_persons: str
    validity_days: str
    booking_delay: str
    cancellation_policy: str
    seasons: List[str]
    days_available: List[str]
    languages: List[str]
    accessibility: List[str]
    equipment_provided: List[str]
    equipment_required: List[str]
```

### ActivityPricing
```python
@dataclass
class ActivityPricing:
    salers: str
    value: float
    value_currency: str
    reimbursement: float
    margin_rate: float
    commission: float
    commission_rate: float
    partner_price: float
    public_price: float
    prices_by_country: Dict[str, float]
```

---

## Utilitaires

### Statistiques
```python
stats = scraper.get_statistics(products)
# Retourne:
# {
#     "total_products": 150,
#     "products_with_details": 150,
#     "products_with_activities": 120,
#     "total_activities": 5000,
#     "prices": {"min": 29.9, "max": 999.0, "avg": 150.0, "count": 150},
#     "by_publisher": {"FRANCE": 100, "BELGIUM": 50},
#     "by_status": {"ACTIVE": 140, "ARCHIVED": 10},
#     "by_universe": {"Week-end": 50, "Séjour": 40, ...},
#     "by_product_type": {"Classique": 120, "Bundle": 30}
# }
```

### Pays disponibles
```python
countries = scraper.get_available_countries()
# ['FR', 'BE', 'ES', 'IT', 'PT', 'NL', 'CH', 'LU', 'MC', 'AD']
```

---

## Interface Streamlit

Lancer l'application:
```bash
streamlit run app.py
```

### Fonctionnalités UI
- **Authentification**: Cookie PHPSESSID ou login/password
- **Lookup produit**: Par ID, avec tous les onglets
- **Lookup activité**: Par ID, avec tous les onglets
- **Recherche en masse**: Par éditeur, statut, avec détails et activités
- **Export**: JSON complet, CSV tableau, CSV détaillé

### Onglets produit
1. Infos (ID, code, statuts, prix, EAN, durées, tags)
2. Descriptions (titre, accroche, bullet points, descriptions multilingues)
3. Merchandising (type, univers, pictogramme, thématiques, cibles)
4. Matérialisations (tableau des codes EAN, DLU)
5. Images (URLs de toutes les images)
6. SEO (meta title, description, keywords)
7. JSON (données brutes)

### Onglets activité
1. Infos (ID, code, statuts, partenaire, coffrets associés)
2. Lieu (adresse complète, GPS, contact)
3. Caractéristiques (durée, poids, capacité, options, saisons)
4. Descriptions (multilingues, conditions, inclus/non inclus)
5. Prix (valeur, partenaire, marges, commissions)
6. JSON (données brutes)

---

## URLs du back-office

| Ressource | URL |
|-----------|-----|
| Recherche produits | `/search/box` |
| Détail produit - Présentation | `/box/index/id/{id}/locale/fr` |
| Détail produit - Caractéristiques | `/box/characteristic/id/{id}/locale/fr` |
| Détail produit - Web | `/box/web/id/{id}/locale/fr` |
| Recherche activités | `/search/activity` |
| Détail activité - Présentation | `/activity/index/id/{id}/locale/fr` |
| Détail activité - Caractéristiques | `/activity/characteristic/id/{id}/locale/fr` |
| Détail lieu | `/location/index/id/{id}` |
