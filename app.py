"""
Wonderbox Scraper - Application Streamlit
==========================================
Interface utilisateur pour le scraping Wonderbox
"""

import streamlit as st
import pandas as pd
import json
import logging
import sys
from datetime import datetime
from dataclasses import asdict

# Configuration logging AVANT les imports
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Imports locaux
from models import Product, ProductDetail, Activity, ActivityDetail
from scraper import WonderboxScraper

logger = logging.getLogger("App")

# Configuration Streamlit
st.set_page_config(
    page_title="Wonderbox Scraper",
    page_icon="🎁",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# SESSION STATE
# ============================================================================

def init_session_state():
    if 'scraper' not in st.session_state:
        st.session_state.scraper = None
    if 'products' not in st.session_state:
        st.session_state.products = []
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    if 'last_product_detail' not in st.session_state:
        st.session_state.last_product_detail = None
    if 'last_activity_detail' not in st.session_state:
        st.session_state.last_activity_detail = None


# ============================================================================
# SIDEBAR - AUTHENTIFICATION
# ============================================================================

def render_sidebar():
    st.sidebar.title("🔐 Authentification")
    
    auth_method = st.sidebar.radio("Méthode", ["Cookies de session", "Login/Password"])
    
    if auth_method == "Cookies de session":
        st.sidebar.markdown("""
        **Comment récupérer le cookie ?**
        1. Va sur `rowbx2.wonderbox.vpn`
        2. F12 → Application → Cookies
        3. Copie `PHPSESSID`
        """)
        
        phpsessid = st.sidebar.text_input("PHPSESSID", type="password", key="phpsessid")
        
        if st.sidebar.button("🔌 Connecter", type="primary", key="btn_connect_cookie"):
            if phpsessid:
                logger.info(f"Tentative connexion avec cookie...")
                st.session_state.scraper = WonderboxScraper(cookies={'PHPSESSID': phpsessid})
                success, message = st.session_state.scraper.test_connection()
                st.session_state.connected = success
                
                if success:
                    st.sidebar.success(f"✅ {message}")
                    logger.info(f"Connexion réussie: {message}")
                else:
                    st.sidebar.error(f"❌ {message}")
                    logger.error(f"Connexion échouée: {message}")
            else:
                st.sidebar.warning("⚠️ Cookie requis")
    else:
        username = st.sidebar.text_input("Utilisateur", key="username")
        password = st.sidebar.text_input("Mot de passe", type="password", key="password")
        
        if st.sidebar.button("🔌 Connecter", type="primary", key="btn_connect_login"):
            if username and password:
                scraper = WonderboxScraper()
                if scraper.login(username, password):
                    st.session_state.scraper = scraper
                    st.session_state.connected = True
                    st.sidebar.success("✅ Connecté")
                else:
                    st.sidebar.error("❌ Échec connexion")
            else:
                st.sidebar.warning("⚠️ Identifiants requis")
    
    # Status
    st.sidebar.markdown("---")
    if st.session_state.connected:
        st.sidebar.success("🟢 Connecté")
        if st.sidebar.button("🔄 Tester connexion"):
            success, msg = st.session_state.scraper.test_connection()
            if success:
                st.sidebar.success(f"✅ {msg}")
            else:
                st.sidebar.error(f"❌ {msg}")
                st.session_state.connected = False
    else:
        st.sidebar.error("🔴 Non connecté")


# ============================================================================
# AFFICHAGE DÉTAIL PRODUIT
# ============================================================================

def display_product_detail(detail: ProductDetail):
    """Affiche les détails d'un produit"""
    if not detail:
        st.error("Aucune donnée à afficher")
        return
    
    st.success(f"✅ **{detail.code}** - {detail.name}")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Infos", "📝 Descriptions", "🏷️ Merchandising", 
        "📦 Matérialisations", "🔧 Debug JSON"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Identifiants**")
            st.write(f"- **ID:** {detail.id}")
            st.write(f"- **Code:** {detail.code}")
            st.write(f"- **Modèle:** {detail.model}")
            st.write(f"- **Collection:** {detail.collection}")
            st.write(f"- **Version:** {detail.version}")
        
        with col2:
            st.markdown("**Codes EAN**")
            for ean in detail.ean_codes[:5]:
                st.write(f"- {ean}")
            
            if detail.characteristics.durations:
                st.markdown("**Durées**")
                st.write(", ".join(detail.characteristics.durations))
    
    with tab2:
        if detail.descriptions.bullet_points:
            st.markdown("**Points clés:**")
            for i, bp in enumerate(detail.descriptions.bullet_points, 1):
                st.write(f"{i}. {bp}")
        
        if detail.descriptions.full_description.get('fr'):
            st.markdown("**Description complète:**")
            st.write(detail.descriptions.full_description['fr'][:1000])
        
        if detail.descriptions.short_description.get('fr'):
            st.markdown("**Description courte:**")
            st.write(detail.descriptions.short_description['fr'])
        
        if detail.descriptions.catch_phrase.get('fr'):
            st.markdown("**Phrase d'accroche:**")
            st.write(detail.descriptions.catch_phrase['fr'])
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Type:** {detail.merchandising.product_type or 'N/A'}")
            st.write(f"**Univers:** {detail.merchandising.universe or 'N/A'}")
            st.write(f"**Pictogramme:** {detail.merchandising.pictogram or 'N/A'}")
        
        with col2:
            if detail.merchandising.thematics:
                st.markdown("**Thématiques:**")
                st.write(", ".join(detail.merchandising.thematics))
            
            if detail.merchandising.target_types:
                st.markdown("**Cibles:**")
                st.write(", ".join(detail.merchandising.target_types))
            
            if detail.merchandising.target_ages:
                st.markdown("**Tranches d'âge:**")
                st.write(", ".join(detail.merchandising.target_ages))
    
    with tab4:
        if detail.materializations:
            mat_data = []
            for m in detail.materializations:
                mat_data.append({
                    "Type": m.type,
                    "Code": m.code,
                    "EAN": m.ean,
                    "DLU": f"{m.dlu} ({m.dlu_type})" if m.dlu_type else m.dlu,
                    "Disponible": "✅" if m.available else "❌"
                })
            st.dataframe(pd.DataFrame(mat_data), hide_index=True, use_container_width=True)
        else:
            st.info("Aucune matérialisation trouvée")
    
    with tab5:
        # JSON pour debug
        st.markdown("**JSON brut (pour debug):**")
        json_data = json.dumps(asdict(detail), indent=2, ensure_ascii=False, default=str)
        st.code(json_data, language="json")


# ============================================================================
# AFFICHAGE DÉTAIL ACTIVITÉ
# ============================================================================

def display_activity_detail(detail: ActivityDetail):
    """Affiche les détails d'une activité"""
    if not detail:
        st.error("Aucune donnée à afficher")
        return
    
    st.success(f"✅ **{detail.code}** - {detail.name}")
    
    tab1, tab2, tab3 = st.tabs(["📋 Infos", "🏨 Lieu", "🔧 Debug JSON"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Identifiants**")
            st.write(f"- **ID:** {detail.id}")
            st.write(f"- **Code:** {detail.code}")
            st.write(f"- **Statut:** {detail.status or 'N/A'}")
        
        with col2:
            st.markdown("**Caractéristiques**")
            st.write(f"- **Durée:** {detail.characteristics.duration or 'N/A'}")
            st.write(f"- **Poids:** {detail.characteristics.weight or 'N/A'}")
            st.write(f"- **Service hôtel:** {'✅' if detail.characteristics.hotel_service else '❌'}")
            st.write(f"- **Chèque manuel:** {'✅' if detail.characteristics.manual_check_allowed else '❌'}")
            
            if detail.characteristics.age_brackets:
                st.write(f"- **Tranches d'âge:** {', '.join(detail.characteristics.age_brackets)}")
    
    with tab2:
        if detail.location.name:
            st.write(f"**Nom:** {detail.location.name}")
            if detail.location.address:
                st.write(f"**Adresse:** {detail.location.address}")
            if detail.location.city:
                st.write(f"**Ville:** {detail.location.zipcode} {detail.location.city}")
            if detail.location.country:
                st.write(f"**Pays:** {detail.location.country}")
        else:
            st.info("Informations de lieu non disponibles")
    
    with tab3:
        json_data = json.dumps(asdict(detail), indent=2, ensure_ascii=False, default=str)
        st.code(json_data, language="json")


# ============================================================================
# LOOKUP PRODUIT
# ============================================================================

def render_product_lookup():
    """Section recherche produit par ID"""
    st.subheader("🔎 Consulter un produit")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        product_id = st.number_input("ID produit", min_value=1, value=32953, key="product_id_input")
    
    with col2:
        fetch_tabs = st.checkbox("Tous les onglets", value=True, key="fetch_all_tabs")
    
    with col3:
        st.write("")  # Spacer
        lookup_btn = st.button("🔍 Rechercher", key="btn_lookup_product", type="primary")
    
    if lookup_btn:
        if not st.session_state.connected:
            st.error("❌ Non connecté")
            return
        
        with st.spinner(f"Chargement du produit {product_id}..."):
            logger.info(f"=== LOOKUP PRODUIT ID={product_id} ===")
            detail = st.session_state.scraper.get_product_detail(product_id, fetch_all_tabs=fetch_tabs)
            
            if detail:
                st.session_state.last_product_detail = detail
                logger.info(f"✅ Produit chargé: {detail.code} - {detail.name}")
            else:
                st.session_state.last_product_detail = None
                st.error(f"""
                ❌ **Produit ID {product_id} non trouvé**
                
                Causes possibles :
                - 🔑 **Session expirée** → Récupère un nouveau cookie PHPSESSID
                - 🌐 **VPN non connecté** → Vérifie ta connexion VPN
                - 📄 **Produit inexistant** → Vérifie l'ID
                
                Regarde les logs dans le terminal pour plus de détails.
                """)
                logger.error(f"Produit ID {product_id} non trouvé")
    
    # Afficher le dernier produit chargé
    if st.session_state.last_product_detail:
        display_product_detail(st.session_state.last_product_detail)


# ============================================================================
# LOOKUP ACTIVITÉ
# ============================================================================

def render_activity_lookup():
    """Section recherche activité par ID"""
    st.subheader("🎯 Consulter une activité")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        activity_id = st.number_input("ID activité", min_value=1, value=529215, key="activity_id_input")
    
    with col2:
        fetch_tabs_act = st.checkbox("Tous les onglets", value=True, key="fetch_all_tabs_act")
    
    with col3:
        st.write("")
        lookup_btn_act = st.button("🔍 Rechercher", key="btn_lookup_activity", type="primary")
    
    if lookup_btn_act:
        if not st.session_state.connected:
            st.error("❌ Non connecté")
            return
        
        with st.spinner(f"Chargement de l'activité {activity_id}..."):
            logger.info(f"=== LOOKUP ACTIVITÉ ID={activity_id} ===")
            detail = st.session_state.scraper.get_activity_detail(activity_id, fetch_all_tabs=fetch_tabs_act)
            
            if detail:
                st.session_state.last_activity_detail = detail
                logger.info(f"✅ Activité chargée: {detail.code} - {detail.name}")
            else:
                st.error(f"❌ Activité ID {activity_id} non trouvée")
                logger.error(f"Activité ID {activity_id} non trouvée")
    
    if st.session_state.last_activity_detail:
        display_activity_detail(st.session_state.last_activity_detail)


# ============================================================================
# RECHERCHE EN MASSE
# ============================================================================

def render_mass_search():
    """Section recherche en masse"""
    st.header("🔍 Recherche en masse")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        publisher = st.selectbox("Éditeur", ["FRANCE", "BELGIUM", "SPAIN", "ITALY"], key="publisher")
    
    with col2:
        web_status = st.selectbox("Statut", ["ACTIVE", "ARCHIVED", "PUBLISHABLE"], key="web_status")
    
    with col3:
        max_pages = st.number_input("Pages max (0=tout)", min_value=0, value=3, key="max_pages")
    
    st.markdown("**Options:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        inc_details = st.checkbox("📋 Détails produits", value=True, key="inc_details")
    
    with col2:
        inc_activities = st.checkbox("🎯 Activités", value=False, key="inc_activities")
    
    with col3:
        inc_act_details = st.checkbox("📝 Détails activités", value=False, key="inc_act_details")
    
    if inc_activities or inc_act_details:
        st.warning("⚠️ **Long !** ~0.5s par produit + ~0.2s par activité")
    
    if st.button("🚀 Lancer le scraping", type="primary", key="btn_mass_search"):
        if not st.session_state.connected:
            st.error("❌ Non connecté")
            return
        
        progress = st.progress(0)
        status = st.empty()
        
        def update_progress(current, total, code, phase):
            progress.progress(current / total if total > 0 else 0)
            status.text(f"{phase}: {current}/{total} - {code}")
        
        with st.spinner("Scraping en cours..."):
            if inc_details or inc_activities:
                products = st.session_state.scraper.get_all_products_with_details(
                    publisher=publisher,
                    web_status=web_status,
                    max_pages=max_pages if max_pages > 0 else None,
                    include_activities=inc_activities,
                    include_activity_details=inc_act_details,
                    progress_callback=update_progress
                )
            else:
                products = st.session_state.scraper.get_all_products(
                    publisher=publisher,
                    web_status=web_status,
                    max_pages=max_pages if max_pages > 0 else None,
                    progress_callback=lambda c, t, n, _: update_progress(c, t, "", "pages")
                )
            
            st.session_state.products = products
            progress.progress(100)
            status.success(f"✅ {len(products)} produits récupérés")


# ============================================================================
# AFFICHAGE RÉSULTATS
# ============================================================================

def render_results():
    """Affiche les résultats du scraping en masse"""
    if not st.session_state.products:
        return
    
    products = st.session_state.products
    
    st.header("📊 Résultats")
    
    # Stats
    cols = st.columns(4)
    cols[0].metric("Produits", len(products))
    
    prices = [p.price for p in products if p.price]
    if prices:
        cols[1].metric("Prix moyen", f"{sum(prices)/len(prices):.0f}€")
    
    has_details = sum(1 for p in products if p.details)
    cols[2].metric("Avec détails", has_details)
    
    total_act = sum(len(p.activities or []) for p in products)
    cols[3].metric("Activités", total_act)
    
    # Tableau
    df_data = []
    for p in products:
        row = {
            'ID': p.id,
            'Code': p.code,
            'Nom': p.name[:40] if p.name else "",
            'Modèle': p.model,
            'Prix': p.price,
            'Activités': len(p.activities) if p.activities else p.activities_count,
        }
        if p.details:
            row['Univers'] = p.details.merchandising.universe
            row['Type'] = p.details.merchandising.product_type
            row['Picto'] = p.details.merchandising.pictogram
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Export
    st.subheader("📥 Export")
    col1, col2 = st.columns(2)
    
    with col1:
        json_data = json.dumps(
            [asdict(p) for p in products],
            indent=2, ensure_ascii=False, default=str
        )
        st.download_button(
            "📋 JSON Complet",
            json_data,
            f"wonderbox_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            "application/json"
        )
    
    with col2:
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            "📄 CSV",
            csv,
            f"wonderbox_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("=" * 60)
    logger.info("  WONDERBOX SCRAPER - DÉMARRAGE")
    logger.info("=" * 60)
    
    init_session_state()
    
    st.title("🎁 Wonderbox Scraper")
    st.markdown("Scraping des produits et activités Rowbx/Wonderbox")
    
    render_sidebar()
    
    if not st.session_state.connected:
        st.warning("""
        ### ⚠️ Non connecté
        
        Connecte-toi via la sidebar avec ton cookie `PHPSESSID`.
        
        **Comment l'obtenir :**
        1. Va sur `http://rowbx2.wonderbox.vpn` (VPN actif)
        2. F12 → Application → Cookies
        3. Copie la valeur de `PHPSESSID`
        """)
        return
    
    # Lookups individuels
    st.markdown("---")
    render_product_lookup()
    
    st.markdown("---")
    render_activity_lookup()
    
    # Recherche en masse
    st.markdown("---")
    render_mass_search()
    
    # Résultats
    render_results()


if __name__ == "__main__":
    main()
