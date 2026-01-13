# Wonderbox Scraper API

Application Streamlit pour scraper les produits et activités Wonderbox depuis le backoffice (Rowbx) et le site public.

## Structure

```
rowbx-api/
├── app.py                    # Interface Streamlit principale
├── common/
│   └── models.py             # Dataclasses partagées
├── services/
│   ├── bo_scraping/          # Scrapers backoffice (VPN requis)
│   │   ├── base_scraper.py
│   │   ├── box_scraper.py
│   │   ├── activity_scraper.py
│   │   └── provider_scraper.py
│   ├── frontend_scraping/    # Scrapers site public
│   │   ├── base_public_scraper.py
│   │   ├── category_scraper.py
│   │   ├── product_scraper.py
│   │   ├── provider_scraper.py
│   │   ├── activity_scraper.py
│   │   └── reviews_scraper.py
│   └── trustpilot_scraping/  # Scraper Trustpilot
│       └── trustpilot_scraper.py
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

Ouvre http://localhost:8501

## Fonctionnalités

### Onglet 1 : Frontend Scraping (Public)
Scrape le site public wonderbox.fr sans authentification :
- **Catégorie** : Liste des produits d'une catégorie
- **Page Produit** : Activités d'un coffret
- **Page Partenaire** : Détails d'un prestataire
- **Page Activité** : Détails d'une activité
- **Avis Partenaire** : Avis clients d'un partenaire

### Onglet 2 : Backoffice Scraping (VPN requis)
Scrape le backoffice Rowbx (nécessite VPN + login) :
- **Produits (Box)** : Recherche avec filtres (status, éditeur, univers)
- **Activités** : Recherche avec filtres (code, ville, thème)
- **Prestataires** : Recherche avec filtres (code, nom, statut)

### Onglet 3 : Trustpilot
Scrape les avis Trustpilot par domaine.

## Export

Tous les résultats peuvent être exportés en JSON et CSV.

## Authentification Backoffice

1. Connecte-toi au VPN Wonderbox
2. Entre ton login/mot de passe dans l'onglet BO
3. L'application gère la session automatiquement

## Structure des données

### Product (BO)
- id, code, name, status
- descriptions, characteristics, merchandising
- materializations, ean_codes

### Activity (BO)
- id, code, name, status
- location (address, city, country)
- characteristics (duration, pricing)

### PublicProduct (Frontend)
- code, name, price, images
- ratings, categories, thematics

### PublicPartner (Frontend)
- code, name, address, contact
- rating, reviews, activities
