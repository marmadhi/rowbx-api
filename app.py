import streamlit as st
import pandas as pd
import json
import logging
import time
from typing import List, Any
from dataclasses import asdict

# Services imports
from services.bo_scraping.box_scraper import BOBoxScraper
from services.bo_scraping.activity_scraper import BOActivityScraper
from services.bo_scraping.provider_scraper import BOProviderScraper
# Frontend imports
from services.frontend_scraping.category_scraper import PublicCategoryScraper
from services.frontend_scraping.product_scraper import PublicProductScraper
from services.frontend_scraping.provider_scraper import PublicProviderScraper
from services.frontend_scraping.activity_scraper import PublicActivityScraper
from services.frontend_scraping.reviews_scraper import PublicReviewsScraper
# Trustpilot import
from services.trustpilot_scraping.trustpilot_scraper import TrustpilotScraper

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("App")

def main():
    st.set_page_config(page_title="Wonderbox Scraper Pro", layout="wide")
    st.title("🏹 Wonderbox Scraper Pro - Microservices")

    tabs = st.tabs(["Frontend Scraping", "Backoffice Scraping", "Trustpilot Scraping"])

    # ========================================================================
    # TAB 1: FRONTEND SCRAPING
    # ========================================================================
    with tabs[0]:
        st.header("Frontend Scraping (Public)")
        
        frontend_mode = st.radio(
            "Type de page à scraper",
            ["Catégorie", "Page Produit (Box)", "Page Partenaire", "Page Activité", "Avis Partenaire"]
        )
        
        url_input = st.text_input("URL de la page (ou Code)", placeholder="https://www.wonderbox.fr/... ou Code")
        
        if st.button("Lancer le scraping Frontend"):
            if not url_input:
                st.error("Veuillez entrer une URL ou un code")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                results = []
                
                try:
                    # Extraction du code si URL
                    code = extract_code_from_url(url_input)
                    status_text.text(f"Code détecté : {code}")
                    
                    if frontend_mode == "Catégorie":
                        scraper = PublicCategoryScraper()
                        status_text.text("Scraping catégorie en cours...")
                        # Récupère tous les produits
                        products = scraper.get_all_products(code, max_pages=5) # Limit 5 for demo
                        results = [asdict(p) for p in products]
                        st.success(f"{len(results)} produits trouvés")
                        
                    elif frontend_mode == "Page Produit (Box)":
                        scraper = PublicProductScraper()
                        status_text.text("Scraping activités du produit...")
                        activities = scraper.get_product_all_activities(code, max_pages=5)
                        results = [asdict(a) for a in activities]
                        st.success(f"{len(results)} activités trouvées")
                        
                    elif frontend_mode == "Page Partenaire":
                        scraper = PublicProviderScraper()
                        status_text.text("Scraping infos partenaire...")
                        partner = scraper.get_partner_details(code)
                        if partner:
                            results = [asdict(partner)]
                            st.json(results[0])
                        
                    elif frontend_mode == "Page Activité":
                        scraper = PublicActivityScraper()
                        details = scraper.get_activity_details(code)
                        if details:
                            results = [details]
                            st.json(results[0])
                            
                    elif frontend_mode == "Avis Partenaire":
                        scraper = PublicReviewsScraper()
                        status_text.text("Scraping avis...")
                        reviews, avg, total = scraper.get_reviews(code, max_pages=5)
                        results = [asdict(r) for r in reviews]
                        st.info(f"Note: {avg}/5 ({total} avis)")
                        
                    # Affichage résultats tableau
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df)
                        display_download_buttons(results, f"frontend_{frontend_mode}_{code}")
                    else:
                        st.warning("Aucun résultat trouvé")
                        
                except Exception as e:
                    st.error(f"Erreur: {e}")
                finally:
                    progress_bar.empty()

    # ========================================================================
    # TAB 2: BACKOFFICE SCRAPING
    # ========================================================================
    with tabs[1]:
        # Layout: Sidebar (Left) | Main (Right)
        col_nav, col_main = st.columns([1, 4])
        
        # --- LEFT SIDEBAR (Login & Navigation) ---
        with col_nav:
            # Custom Style for this column (User Request)
            st.markdown(
                """
                <style>
                .st-emotion-cache-j5r0tf {
                    background-color: #000 !important;
                    padding: 15px !important;
                    border-radius: 10px !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            st.subheader("Connexion")
            username = st.text_input("Login", placeholder="Votre login")
            password = st.text_input("Password", type="password")
            
            if "bo_scraper_box" not in st.session_state:
                st.session_state.bo_scraper_box = BOBoxScraper()
                
            if st.button("Connexion BO", use_container_width=True):
                success = st.session_state.bo_scraper_box.login(username, password)
                if success:
                    st.session_state.bo_connected = True
                    st.success("Connecté ✅")
                else:
                    st.error("Erreur ❌")

            st.markdown("---")
            if st.session_state.get("bo_connected"):
                st.subheader("Navigation")
                bo_mode = st.radio("Entité", ["Produits (Box)", "Activités", "Prestataires"], label_visibility="collapsed")
            else:
                st.info("Veuillez vous connecter")
                bo_mode = None

        # --- RIGHT MAIN (Content) ---
        with col_main:
            st.header("Backoffice Scraping (BO)")
            
            if st.session_state.get("bo_connected") and bo_mode:
                # --- FILTERS UI ---
                filters = {}
                # search_page moved to per-mode blocks for custom layout
                
                if bo_mode == "Produits (Box)":
                    # --- OPTIONS LISTS (Extracted from User HTML) ---
                    UNIVERSE_OPTIONS = {
                    "STAY": "Week-end",
                    "GASTRONOMY": "Gastronomie",
                    "WELLNESS": "Bien-être",
                    "ADVENTURE": "Sport & Aventure",
                    "ENTERTAINMENT": "Loisirs",
                    "MULTITHEMATIC": "Multi-thématique"
                }
                
                THEMATIC_OPTIONS = {
                    "BNB": "BnB",
                    "GASTRONOMY": "Gastronomie",
                    "WELLNESS": "Bien être",
                    "PLANE_TICKETS": "Billets d'avion",
                    "BREAKFAST": "Petit-déjeuner",
                    "RESTAURANT": "Restaurant",
                    "TASTING_APERITIF": "Dégustation / Apéro",
                    "COOKING_COURSES": "Atelier culinaire",
                    "OENOLOGY": "Oenologie",
                    "CARE_MASSAGE": "Soin et massage",
                    "SPA_THALASSO": "Spa et thalasso",
                    "BEAUTY": "Beauté",
                    "SKIDIVING": "Parachute",
                    "DRIVING": "Pilotage",
                    "HOT_AIR_BALLOON": "Montgolfière",
                    "PARAGLIDING": "Parapente",
                    "BUNGEE_JUMPING": "Saut à l'élastique",
                    "HELICOPTER": "Hélicoptère",
                    "ULM_AIRCRAFT": "ULM",
                    "OUTDOOR": "Outdoor",
                    "INDOOR": "Indoor",
                    "AQUATIC": "Nautique",
                    "AMUSEMENT_PARK_ZOO": "Parc d'attractions et zoos",
                    "VIDEOGAMES_ESPORT": "Jeux vidéo & Esport",
                    "PHOTO_SHOOTING": "Shooting photo",
                    "CULTURE": "Culture",
                    "SHOW_THEATER": "Spectacle",
                    "CONCERT": "Concert",
                    "MUSEUM_MONUMENTS": "Musées & Monuments",
                    "CINEMA": "Cinéma",
                    "SPORTING_EVENTS": "Evènements sportifs",
                    "FOOTBALL": "Football",
                    "RUGBY": "Rugby",
                    "BASKETBALL": "Basket",
                    "TENNIS": "Tennis",
                    "CREATIVE_WORKSHOPS": "Ateliers créatifs",
                    "GENERIC": "Générique",
                    "MULTI_THEMATIC": "Multi-thématiques",
                    "FREE_THEMATIC_1": "Thématique libre 1",
                    "FREE_THEMATIC_2": "Thématique libre 2",
                    "FREE_THEMATIC_3": "Thématique libre 3"
                }
                
                PUBLISHER_OPTIONS = {
                    "BELGIUM": "Belgique",
                    "DENMARK": "Danemark",
                    "FRANCE": "France",
                    "ITALY": "Italie",
                    "NETHERLANDS": "Pays-Bas",
                    "NORWAY": "Norvège",
                    "PORTUGAL": "Portugal",
                    "SPAIN": "Espagne",
                    "SWEDEN": "Suède",
                    "SWITZERLAND": "Suisse",
                    "UK": "Royaume-Uni",
                    "USA": "USA"
                }

                # --- COMPACT LAYOUT: 5 Columns ---
                col1, col2, col3, col4, col5 = st.columns(5)
                
                search_page = col1.number_input("Page", min_value=1, value=1)
                f_status = col2.selectbox("Statut Web", ["", "ACTIVE", "INACTIVE", "ARCHIVED"], index=1)
                
                pub_keys = [""] + list(PUBLISHER_OPTIONS.keys())
                f_publisher = col3.selectbox(
                    "Pays éditeur", 
                    options=pub_keys,
                    format_func=lambda x: PUBLISHER_OPTIONS.get(x, "Tous") if x else "Tous"
                )
                
                # Helper for selectbox with labels
                univ_keys = [""] + list(UNIVERSE_OPTIONS.keys())
                f_universe = col4.selectbox(
                    "Univers", 
                    options=univ_keys, 
                    format_func=lambda x: UNIVERSE_OPTIONS.get(x, "Tous") if x else "Tous"
                )
                
                them_keys = [""] + list(THEMATIC_OPTIONS.keys())
                f_thematic = col5.selectbox(
                    "Thématique", 
                    options=them_keys,
                    format_func=lambda x: THEMATIC_OPTIONS.get(x, "Tous") if x else "Tous"
                )

                # Logic preparation (No Code, No JSON)
                if f_status: filters["boxPublishStatus_webStatus"] = f_status
                if f_publisher: filters["publisher"] = f_publisher
                if f_universe: filters["merchandising_universe"] = f_universe
                if f_thematic: filters["merchandising_boxThematics"] = f_thematic

            elif bo_mode == "Activités":
                search_page = st.number_input("Page", min_value=1, value=1)
                col1, col2, col3, col4 = st.columns(4)
                f_code = col1.text_input("Code Activité")
                f_status = col2.selectbox("Statut Web", ["", "ACTIVE", "INACTIVE", "ARCHIVED"], index=1)
                f_publisher = col3.selectbox("Publisher", ["", "FRANCE", "BELGIUM", "SPAIN", "ITALY"], index=1)
                f_universe = col4.selectbox("Univers", ["", "GASTRONOMY", "STAY", "WELLNESS", "ADVENTURE", "ENTERTAINMENT"])
                
                col5, col6, col7 = st.columns(3)
                f_city = col5.text_input("Ville")
                f_zip = col6.text_input("Code Postal")
                f_theme = col7.text_input("Thème (Code)")
                
                with st.expander("Filtres Avancés (JSON)", expanded=False):
                    default_json = '{\n  "multibrand": "1",\n  "target_type": ["COUPLE"]\n}'
                    json_input = st.text_area("JSON Configuration", value="", placeholder=default_json, height=150, key="json_act")

                # Logic preparation
                if f_code: filters["code"] = f_code
                if f_status: filters["boxPublishStatus_webStatus"] = f_status
                if f_publisher: filters["publisher"] = f_publisher
                if f_universe: filters["universe"] = f_universe
                if f_city: filters["city"] = f_city
                if f_zip: filters["zipCode"] = f_zip
                if f_theme: filters["theme"] = f_theme
                
                if json_input.strip():
                    try:
                        filters.update(json.loads(json_input))
                    except json.JSONDecodeError:
                        st.error("JSON Invalide")

            elif bo_mode == "Prestataires":
                search_page = st.number_input("Page", min_value=1, value=1)
                col1, col2, col3 = st.columns(3)
                f_code = col1.text_input("Code/ID Partenaire")
                f_status = col2.selectbox("Statut Web", ["", "ACTIVE", "INACTIVE"], index=1)
                f_publisher = col3.selectbox("Publisher", ["", "FRANCE", "BELGIUM"], index=1)
                
                col4, col5, col6 = st.columns(3)
                f_name = col4.text_input("Nom Partenaire")
                f_city = col5.text_input("Ville")
                f_zip = col6.text_input("Code Postal")
                
                with st.expander("Filtres Avancés (JSON)", expanded=False):
                    default_json = '{\n  "country": "FR"\n}'
                    json_input = st.text_area("JSON Configuration", value="", placeholder=default_json, height=100, key="json_prov")

                # Logic preparation
                if f_code: filters["code"] = f_code
                if f_status: filters["boxPublishStatus_webStatus"] = f_status
                if f_publisher: filters["publisher"] = f_publisher
                if f_name: filters["name"] = f_name
                if f_city: filters["city"] = f_city
                if f_zip: filters["zipCode"] = f_zip
                
                if json_input.strip():
                    try:
                        filters.update(json.loads(json_input))
                    except json.JSONDecodeError:
                        st.error("JSON Invalide")

            # --- ACTION ---
            col_act1, col_act2 = st.columns([1, 2])
            scrape_all = col_act2.checkbox("Scraper toutes les pages (Exhaustif)", value=False)
            
            if col_act1.button("Rechercher BO"):
                status_text = st.empty()
                progress_bar = st.empty()
                results = []
                
                try:
                    # 1. Initial Search (Page 1 or selected page)
                    current_page = 1 if scrape_all else search_page
                    status_text.text(f"Récupération page {current_page}...")
                    
                    if bo_mode == "Produits (Box)":
                        scraper = BOBoxScraper(session=st.session_state.bo_scraper_box.session)
                        items, total_count, total_pages = scraper.search_products(filters=filters, page=current_page)
                    elif bo_mode == "Activités":
                        scraper = BOActivityScraper(session=st.session_state.bo_scraper_box.session)
                        items, total_count, total_pages = scraper.search_activities(filters=filters, page=current_page)
                    elif bo_mode == "Prestataires":
                        scraper = BOProviderScraper(session=st.session_state.bo_scraper_box.session)
                        items, total_count, total_pages = scraper.search_providers(filters=filters, page=current_page)
                    
                    results.extend([asdict(i) for i in items])
                    
                    # 2. Pagination Loop if requested
                    if scrape_all and total_pages > 1:
                        progress_bar.progress(1 / total_pages)
                        
                        for p in range(2, total_pages + 1):
                            status_text.text(f"Récupération page {p}/{total_pages}...")
                            
                            if bo_mode == "Produits (Box)":
                                items, _, _ = scraper.search_products(filters=filters, page=p)
                            elif bo_mode == "Activités":
                                items, _, _ = scraper.search_activities(filters=filters, page=p)
                            elif bo_mode == "Prestataires":
                                items, _, _ = scraper.search_providers(filters=filters, page=p)
                                
                            results.extend([asdict(i) for i in items])
                            progress_bar.progress(p / total_pages)
                            time.sleep(0.1) # Be nice
                            
                        progress_bar.empty()

                    status_text.text(f"Terminé : {len(results)} items récupérés sur {total_count} disponibles.")
                    
                    if results:
                        df = pd.DataFrame(results)
                        st.dataframe(df)
                        display_download_buttons(results, f"bo_{bo_mode}_all" if scrape_all else f"bo_{bo_mode}_page{search_page}")
                        
                except Exception as e:
                    st.error(f"Erreur BO: {e}")

    # ========================================================================
    # TAB 3: TRUSTPILOT SCRAPING
    # ========================================================================
    with tabs[2]:
        st.header("Trustpilot Scraping")
        domain = st.text_input("Domaine Trustpilot (ex: wonderbox.fr, amazon.fr)", value="wonderbox.fr")
        pages = st.number_input("Nombre de pages", 1, 100, 5)
        
        if st.button("Scraper Trustpilot"):
            scraper = TrustpilotScraper()
            with st.spinner(f"Scraping {domain}..."):
                reviews = scraper.get_reviews(domain, pages=pages)
                
            results = [asdict(r) for r in reviews]
            st.success(f"{len(results)} avis récupérés")
            
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df)
                display_download_buttons(results, f"trustpilot_{domain}")

def extract_code_from_url(url_or_code: str) -> str:
    """Helper simple pour extraire un code d'une URL ou retourner le code"""
    if "http" not in url_or_code:
        return url_or_code
    
    # Ex: wonderbox.fr/b/B123
    import re
    match = re.search(r'/[bc]/([A-Z0-9]+)', url_or_code) # Box or Category
    if match: return match.group(1)
    
    match = re.search(r'/l/([A-Z0-9]+)', url_or_code) # Partner
    if match: return match.group(1)
    
    match = re.search(r'activityId=(\d+)', url_or_code)
    if match: return match.group(1)
    
    # URL directe /a/CODE
    match = re.search(r'/a/([A-Z0-9]+)', url_or_code) 
    if match: return match.group(1)

    return url_or_code.split('/')[-1]

def display_download_buttons(data: List[Any], filename: str):
    """Affiche les boutons export JSON/CSV"""
    json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    st.download_button("Télécharger JSON", json_str, file_name=f"{filename}.json", mime="application/json")
    
    if data:
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger CSV", csv, file_name=f"{filename}.csv", mime="text/csv")

if __name__ == "__main__":
    main()
