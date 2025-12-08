# 🎁 Wonderbox Scraper

Application Streamlit pour scraper les produits et activités Wonderbox depuis Rowbx.

## 📁 Structure

```
wonderbox_scraper/
├── app.py           # Interface Streamlit
├── scraper.py       # Classe WonderboxScraper avec logs
├── models.py        # Dataclasses (Product, Activity, etc.)
├── requirements.txt
└── README.md
```

## 🚀 Installation

```bash
cd wonderbox_scraper
pip install -r requirements.txt
```

## ▶️ Lancement

```bash
streamlit run app.py
```

Ouvre http://localhost:8501

## 🔐 Authentification

1. Connecte-toi à `http://rowbx2.wonderbox.vpn` (VPN actif)
2. F12 → Application → Cookies
3. Copie `PHPSESSID`
4. Colle dans l'app

## 📊 Fonctionnalités

### Lookup individuel
- Recherche un **produit** par ID (ex: 32953)
- Recherche une **activité** par ID (ex: 529215)
- Affiche tous les détails avec onglets

### Recherche en masse
- Scrape tous les produits par éditeur/statut
- Options : détails produits, activités, détails activités
- Export JSON et CSV

## 🐛 Debug

Les logs s'affichent dans le terminal avec niveau DEBUG.

Fichiers HTML sauvegardés dans `/tmp/` :
- `debug_product_{id}_tab1.html`
- `debug_activity_{id}_tab1.html`

## 📦 Structure des données

### ProductDetail
```
├── id, code, name, model, collection, version
├── descriptions
│   ├── title, catch_phrase, bullet_points
│   ├── short_description, full_description
│   └── target_description, program_description
├── characteristics
│   └── tags, durations, meta_title/keywords/description
├── merchandising
│   └── product_type, universe, pictogram, thematics, targets
├── materializations[]
│   └── type, code, ean, dlu, available
└── ean_codes[]
```

### ActivityDetail
```
├── id, code, name, status
├── location
│   └── id, name, address, city, country
├── characteristics
│   └── duration, weight, age_brackets, hotel_service
└── pricing
```
