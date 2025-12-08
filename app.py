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
    """Affiche les détails complets d'un produit"""
    if not detail:
        st.error("Aucune donnée à afficher")
        return

    st.success(f"**{detail.code}** - {detail.name}")

    # Tabs enrichis
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Infos", "Descriptions", "Merchandising",
        "Matérialisations", "Images", "SEO", "JSON"
    ])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Identifiants**")
            st.write(f"- **ID:** {detail.id}")
            st.write(f"- **Code:** {detail.code}")
            st.write(f"- **Modèle:** {detail.model}")
            st.write(f"- **Collection:** {detail.collection}")
            st.write(f"- **Version:** {detail.version}")

        with col2:
            st.markdown("**Statuts**")
            st.write(f"- **Publisher:** {detail.publisher or 'N/A'}")
            st.write(f"- **Status:** {detail.status or 'N/A'}")
            st.write(f"- **Web Status:** {detail.web_status or 'N/A'}")
            if detail.price:
                st.write(f"- **Prix:** {detail.price:.2f} EUR")

        with col3:
            st.markdown("**Codes EAN**")
            for ean in detail.ean_codes[:5]:
                st.write(f"- `{ean}`")

            if detail.characteristics.durations:
                st.markdown("**Durées (nuits)**")
                st.write(", ".join(detail.characteristics.durations))

        # Caractéristiques supplémentaires
        if detail.characteristics.tags or detail.characteristics.favorite_activities:
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if detail.characteristics.tags:
                    st.markdown("**Tags**")
                    st.write(", ".join(detail.characteristics.tags))
            with col2:
                if detail.characteristics.favorite_activities:
                    st.markdown("**Activités favorites**")
                    st.write(", ".join(detail.characteristics.favorite_activities))

        # Booklets
        if detail.characteristics.booklet_url_with_addresses or detail.characteristics.booklet_url_without_addresses:
            st.markdown("---")
            st.markdown("**Livrets**")
            if detail.characteristics.booklet_url_with_addresses:
                st.write(f"[Avec adresses]({detail.characteristics.booklet_url_with_addresses})")
            if detail.characteristics.booklet_url_without_addresses:
                st.write(f"[Sans adresses]({detail.characteristics.booklet_url_without_addresses})")

    with tab2:
        # Descriptions multilingues
        if detail.descriptions.title:
            st.markdown("**Titre**")
            for lang, text in detail.descriptions.title.items():
                st.write(f"- [{lang}] {text}")

        if detail.descriptions.catch_phrase:
            st.markdown("**Phrase d'accroche**")
            for lang, text in detail.descriptions.catch_phrase.items():
                st.write(f"- [{lang}] {text[:200]}...")

        if detail.descriptions.bullet_points:
            st.markdown("**Points clés**")
            for i, bp in enumerate(detail.descriptions.bullet_points, 1):
                st.write(f"{i}. {bp[:150]}...")

        if detail.descriptions.short_description:
            st.markdown("**Description courte**")
            for lang, text in detail.descriptions.short_description.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.full_description:
            st.markdown("**Description complète**")
            for lang, text in detail.descriptions.full_description.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.target_description:
            st.markdown("**Description cible**")
            for lang, text in detail.descriptions.target_description.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.program_description:
            st.markdown("**Programme**")
            for lang, text in detail.descriptions.program_description.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.why_you_will_love:
            st.markdown("**Pourquoi vous allez aimer**")
            for lang, text in detail.descriptions.why_you_will_love.items():
                st.write(f"- [{lang}] {text[:200]}...")

        if detail.descriptions.video_link:
            st.markdown("**Liens vidéo**")
            for lang, url in detail.descriptions.video_link.items():
                st.write(f"- [{lang}] {url}")

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Classification**")
            st.write(f"- **Type:** {detail.merchandising.product_type or 'N/A'}")
            st.write(f"- **Univers:** {detail.merchandising.universe or 'N/A'}")
            st.write(f"- **Pictogramme:** {detail.merchandising.pictogram or 'N/A'}")

            if detail.merchandising.thematics:
                st.markdown("**Thématiques**")
                for t in detail.merchandising.thematics:
                    st.write(f"- {t}")

        with col2:
            st.markdown("**Ciblage**")
            if detail.merchandising.target_types:
                st.write(f"**Types:** {', '.join(detail.merchandising.target_types)}")
            if detail.merchandising.target_ages:
                st.write(f"**Ages:** {', '.join(detail.merchandising.target_ages)}")
            if detail.merchandising.target_numbers:
                st.write(f"**Nb personnes:** {', '.join(detail.merchandising.target_numbers)}")

    with tab4:
        if detail.materializations:
            mat_data = []
            for m in detail.materializations:
                mat_data.append({
                    "Type": m.type,
                    "Code": m.code,
                    "EAN": m.ean,
                    "DLU": f"{m.dlu} ({m.dlu_type})" if m.dlu_type else m.dlu,
                    "Disponible": "Oui" if m.available else "Non"
                })
            st.dataframe(pd.DataFrame(mat_data), hide_index=True, use_container_width=True)
        else:
            st.info("Aucune matérialisation trouvée")

    with tab5:
        st.markdown("**Images du produit**")
        col1, col2 = st.columns(2)
        with col1:
            if detail.images.edito:
                st.write(f"**Edito:** {detail.images.edito}")
            if detail.images.facing_2d:
                st.write(f"**Facing 2D:** {detail.images.facing_2d}")
            if detail.images.simul_3d:
                st.write(f"**Simul 3D:** {detail.images.simul_3d}")
            if detail.images.landscape:
                st.write(f"**Paysage:** {detail.images.landscape}")
        with col2:
            if detail.images.lengow:
                st.write(f"**Lengow:** {detail.images.lengow}")
            if detail.images.back_card:
                st.write(f"**Verso:** {detail.images.back_card}")
            if detail.images.squared:
                st.write(f"**Carré:** {detail.images.squared}")
            if detail.images.header:
                st.write(f"**Headers:** {len(detail.images.header)} images")

    with tab6:
        st.markdown("**SEO / Meta**")
        if detail.characteristics.meta_title:
            st.markdown("**Meta Title**")
            for lang, text in detail.characteristics.meta_title.items():
                st.write(f"- [{lang}] {text}")

        if detail.characteristics.meta_description:
            st.markdown("**Meta Description**")
            for lang, text in detail.characteristics.meta_description.items():
                st.write(f"- [{lang}] {text[:150]}...")

        if detail.characteristics.meta_keywords:
            st.markdown("**Meta Keywords**")
            for lang, text in detail.characteristics.meta_keywords.items():
                st.write(f"- [{lang}] {text}")

    with tab7:
        st.markdown("**JSON brut**")
        json_data = json.dumps(asdict(detail), indent=2, ensure_ascii=False, default=str)
        st.code(json_data, language="json")


# ============================================================================
# AFFICHAGE DÉTAIL ACTIVITÉ
# ============================================================================

def display_activity_detail(detail: ActivityDetail):
    """Affiche les détails complets d'une activité"""
    if not detail:
        st.error("Aucune donnée à afficher")
        return

    st.success(f"**{detail.code}** - {detail.name}")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Infos", "Lieu", "Caractéristiques", "Descriptions", "Prix", "JSON"
    ])

    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Identifiants**")
            st.write(f"- **ID:** {detail.id}")
            st.write(f"- **Code:** {detail.code}")
            st.write(f"- **Target:** {detail.target or 'N/A'}")

        with col2:
            st.markdown("**Statuts**")
            st.write(f"- **Status:** {detail.status or 'N/A'}")
            st.write(f"- **Web Status:** {detail.web_status or 'N/A'}")
            st.write(f"- **Publisher:** {detail.publisher or 'N/A'}")

        with col3:
            st.markdown("**Partenaire**")
            st.write(f"- **Nom:** {detail.partner_name or 'N/A'}")
            st.write(f"- **Code:** {detail.partner_code or 'N/A'}")

        # Produits associés
        if detail.products:
            st.markdown("---")
            st.markdown("**Coffrets associés**")
            st.write(", ".join(detail.products))

        # Images
        if detail.images:
            st.markdown("---")
            st.markdown(f"**Images:** {len(detail.images)}")

    with tab2:
        if detail.location.name or detail.location.id:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Adresse**")
                st.write(f"- **ID:** {detail.location.id}")
                st.write(f"- **Nom:** {detail.location.name}")
                if detail.location.address:
                    st.write(f"- **Adresse:** {detail.location.address}")
                if detail.location.zipcode or detail.location.city:
                    st.write(f"- **Ville:** {detail.location.zipcode} {detail.location.city}")
                if detail.location.country:
                    st.write(f"- **Pays:** {detail.location.country}")

            with col2:
                st.markdown("**Infos supplémentaires**")
                if detail.location.region:
                    st.write(f"- **Région:** {detail.location.region}")
                if detail.location.department:
                    st.write(f"- **Département:** {detail.location.department}")
                if detail.location.phone:
                    st.write(f"- **Téléphone:** {detail.location.phone}")
                if detail.location.email:
                    st.write(f"- **Email:** {detail.location.email}")
                if detail.location.website:
                    st.write(f"- **Site web:** {detail.location.website}")
                if detail.location.latitude and detail.location.longitude:
                    st.write(f"- **GPS:** {detail.location.latitude}, {detail.location.longitude}")
        else:
            st.info("Informations de lieu non disponibles")

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Général**")
            st.write(f"- **Durée:** {detail.characteristics.duration or 'N/A'}")
            st.write(f"- **Poids:** {detail.characteristics.weight or 'N/A'}")
            st.write(f"- **Type:** {detail.characteristics.activity_type or 'N/A'}")
            st.write(f"- **Sous-type:** {detail.characteristics.activity_subtype or 'N/A'}")
            st.write(f"- **Type chambre:** {detail.characteristics.room_type or 'N/A'}")
            st.write(f"- **Nb personnes:** {detail.characteristics.nb_persons or 'N/A'}")

            if detail.characteristics.capacity_min or detail.characteristics.capacity_max:
                st.write(f"- **Capacité:** {detail.characteristics.capacity_min} - {detail.characteristics.capacity_max}")

        with col2:
            st.markdown("**Options**")
            st.write(f"- **Service hôtel:** {'Oui' if detail.characteristics.hotel_service else 'Non'}")
            st.write(f"- **Chèque manuel:** {'Oui' if detail.characteristics.manual_check_allowed else 'Non'}")
            st.write(f"- **Résa obligatoire:** {'Oui' if detail.characteristics.reservation_required else 'Non'}")

            if detail.characteristics.day_moment:
                st.write(f"- **Moment journée:** {detail.characteristics.day_moment}")
            if detail.characteristics.meal_moment:
                st.write(f"- **Moment repas:** {detail.characteristics.meal_moment}")
            if detail.characteristics.family:
                st.write(f"- **Famille:** {detail.characteristics.family}")

        # Listes
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if detail.characteristics.age_brackets:
                st.markdown("**Tranches d'âge**")
                st.write(", ".join(detail.characteristics.age_brackets))
            if detail.characteristics.seasons:
                st.markdown("**Saisons**")
                st.write(", ".join(detail.characteristics.seasons))
            if detail.characteristics.days_available:
                st.markdown("**Jours disponibles**")
                st.write(", ".join(detail.characteristics.days_available))

        with col2:
            if detail.characteristics.languages:
                st.markdown("**Langues**")
                st.write(", ".join(detail.characteristics.languages))
            if detail.characteristics.accessibility:
                st.markdown("**Accessibilité**")
                st.write(", ".join(detail.characteristics.accessibility))
            if detail.characteristics.equipment_provided:
                st.markdown("**Équipement fourni**")
                st.write(", ".join(detail.characteristics.equipment_provided))

    with tab4:
        has_desc = False
        if detail.descriptions.name:
            has_desc = True
            st.markdown("**Nom**")
            for lang, text in detail.descriptions.name.items():
                st.write(f"- [{lang}] {text}")

        if detail.descriptions.description:
            has_desc = True
            st.markdown("**Description**")
            for lang, text in detail.descriptions.description.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.short_description:
            has_desc = True
            st.markdown("**Description courte**")
            for lang, text in detail.descriptions.short_description.items():
                st.write(f"- [{lang}] {text[:200]}...")

        if detail.descriptions.conditions:
            has_desc = True
            st.markdown("**Conditions**")
            for lang, text in detail.descriptions.conditions.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.practical_info:
            has_desc = True
            st.markdown("**Infos pratiques**")
            for lang, text in detail.descriptions.practical_info.items():
                with st.expander(f"[{lang}]"):
                    st.write(text)

        if detail.descriptions.included:
            has_desc = True
            st.markdown("**Inclus**")
            for lang, text in detail.descriptions.included.items():
                st.write(f"- [{lang}] {text}")

        if detail.descriptions.not_included:
            has_desc = True
            st.markdown("**Non inclus**")
            for lang, text in detail.descriptions.not_included.items():
                st.write(f"- [{lang}] {text}")

        if not has_desc:
            st.info("Aucune description disponible")

    with tab5:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Prix**")
            if detail.price:
                st.write(f"- **Prix:** {detail.price:.2f} EUR")
            if detail.price_countries:
                st.write(f"- **Pays:** {detail.price_countries}")

            st.markdown("**Pricing détaillé**")
            if detail.pricing.value:
                st.write(f"- **Valeur:** {detail.pricing.value:.2f} EUR")
            if detail.pricing.partner_price:
                st.write(f"- **Prix partenaire:** {detail.pricing.partner_price:.2f} EUR")
            if detail.pricing.public_price:
                st.write(f"- **Prix public:** {detail.pricing.public_price:.2f} EUR")

        with col2:
            st.markdown("**Marges et commissions**")
            if detail.pricing.reimbursement:
                st.write(f"- **Remboursement:** {detail.pricing.reimbursement:.2f} EUR")
            if detail.pricing.margin_rate:
                st.write(f"- **Taux marge:** {detail.pricing.margin_rate:.2f}%")
            if detail.pricing.commission:
                st.write(f"- **Commission:** {detail.pricing.commission:.2f} EUR")
            if detail.pricing.commission_rate:
                st.write(f"- **Taux commission:** {detail.pricing.commission_rate:.2f}%")
            if detail.pricing.salers:
                st.write(f"- **Salers:** {detail.pricing.salers}")

    with tab6:
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
    """Affiche les résultats du scraping en masse avec statistiques enrichies"""
    if not st.session_state.products:
        return

    products = st.session_state.products

    st.header("Résultats")

    # Stats enrichies
    cols = st.columns(5)
    cols[0].metric("Produits", len(products))

    prices = [p.price for p in products if p.price]
    if prices:
        cols[1].metric("Prix moyen", f"{sum(prices)/len(prices):.0f} EUR")
        cols[2].metric("Prix min/max", f"{min(prices):.0f} - {max(prices):.0f} EUR")

    has_details = sum(1 for p in products if p.details)
    cols[3].metric("Avec détails", has_details)

    total_act = sum(len(p.activities or []) for p in products)
    cols[4].metric("Activités", total_act)

    # Stats par éditeur
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Par éditeur**")
        by_publisher = {}
        for p in products:
            pub = p.publisher or "Unknown"
            by_publisher[pub] = by_publisher.get(pub, 0) + 1
        for pub, count in sorted(by_publisher.items(), key=lambda x: -x[1]):
            st.write(f"- {pub}: {count}")

    with col2:
        st.markdown("**Par statut**")
        by_status = {}
        for p in products:
            status = p.status or p.web_status or "Unknown"
            by_status[status] = by_status.get(status, 0) + 1
        for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
            st.write(f"- {status}: {count}")

    with col3:
        st.markdown("**Par univers**")
        by_universe = {}
        for p in products:
            if p.details and p.details.merchandising.universe:
                universe = p.details.merchandising.universe
                by_universe[universe] = by_universe.get(universe, 0) + 1
        for universe, count in sorted(by_universe.items(), key=lambda x: -x[1])[:5]:
            st.write(f"- {universe}: {count}")

    # Tableau enrichi
    st.markdown("---")
    st.subheader("Tableau des produits")

    df_data = []
    for p in products:
        row = {
            'ID': p.id,
            'Code': p.code,
            'Nom': p.name[:50] if p.name else "",
            'Modèle': p.model,
            'Collection': p.collection,
            'Publisher': p.publisher,
            'Status': p.status,
            'Web Status': p.web_status,
            'Type': p.product_type,
            'Prix': p.price,
            'Pays prix': p.price_country,
            'Validité': p.validity_duration,
            'Activités': len(p.activities) if p.activities else p.activities_count,
            'EAN': p.ean_code,
        }
        if p.details:
            row['Univers'] = p.details.merchandising.universe
            row['Pictogramme'] = p.details.merchandising.pictogram
            row['Thématiques'] = ', '.join(p.details.merchandising.thematics[:3]) if p.details.merchandising.thematics else ''
            row['Cibles'] = ', '.join(p.details.merchandising.target_types[:2]) if p.details.merchandising.target_types else ''
            row['Durées'] = ', '.join(p.details.characteristics.durations[:3]) if p.details.characteristics.durations else ''
        df_data.append(row)

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    # Export enrichi
    st.markdown("---")
    st.subheader("Export")
    col1, col2, col3 = st.columns(3)

    with col1:
        json_data = json.dumps(
            [asdict(p) for p in products],
            indent=2, ensure_ascii=False, default=str
        )
        st.download_button(
            "JSON Complet",
            json_data,
            f"wonderbox_full_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            "application/json"
        )

    with col2:
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            "CSV Tableau",
            csv,
            f"wonderbox_table_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv"
        )

    with col3:
        # Export CSV détaillé
        detailed_data = []
        for p in products:
            row = {
                'id': p.id,
                'code': p.code,
                'name': p.name,
                'model': p.model,
                'collection': p.collection,
                'version': p.version,
                'publisher': p.publisher,
                'status': p.status,
                'web_status': p.web_status,
                'product_type': p.product_type,
                'price': p.price,
                'price_country': p.price_country,
                'validity_duration': p.validity_duration,
                'production_year': p.production_year,
                'activities_count': p.activities_count,
                'ean_code': p.ean_code,
            }
            if p.details:
                row['universe'] = p.details.merchandising.universe
                row['pictogram'] = p.details.merchandising.pictogram
                row['thematics'] = '|'.join(p.details.merchandising.thematics)
                row['target_types'] = '|'.join(p.details.merchandising.target_types)
                row['target_ages'] = '|'.join(p.details.merchandising.target_ages)
                row['durations'] = '|'.join(p.details.characteristics.durations)
                row['tags'] = '|'.join(p.details.characteristics.tags)
                row['ean_codes'] = '|'.join(p.details.ean_codes)
                row['short_desc_fr'] = p.details.descriptions.short_description.get('fr', '')[:500]
                row['catch_phrase_fr'] = p.details.descriptions.catch_phrase.get('fr', '')[:200]
            detailed_data.append(row)

        detailed_df = pd.DataFrame(detailed_data)
        detailed_csv = detailed_df.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button(
            "CSV Détaillé",
            detailed_csv,
            f"wonderbox_detailed_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
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
