# -*- coding: utf-8 -*-

############################
# Application Vidocq (stable)
# Last update : 2025/11/07 #
############################

import io
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import sys, os

# --- Imports internes ---
sys.path.append(os.path.join(os.path.dirname(__file__), "code", "core"))
from concept_extractor import (
    extract_exact_concepts,
    extract_semantic_concepts,
    extract_tfidf_concepts,
    extract_top_semantic_concepts
)
from entity_extractor import get_entity_cache

sys.path.append(os.path.join(os.path.dirname(__file__), "code", "visualization"))
from graph_builder import build_graph
from graph_display import display_graph, export_graph_image
from lib.indexing import get_index_manager
from word_cloud_builder import generate_wordcloud
from event_map import build_event_markers, markers_to_rows, render_event_map

# --- Initialisation ---
index_manager = get_index_manager()
entity_cache = get_entity_cache()
st.set_page_config(layout="wide")

# --- Style cyber ---
def set_cyber_style():
    css = """
    <style>
    .stApp { background: linear-gradient(to bottom, #002a2d, #d2ac7a); color: #00ffcc; font-family: 'Courier New', monospace; }
    h1,h2,h3,h4,h5,h6 { color: #003300; text-shadow:-1px -1px 0 #FFA07A,1px -1px 0 #FFA07A,-1px  1px 0 #FFA07A,1px  1px 0 #FFA07A; }
    .stTextInput input { color: black !important; background-color: white !important; }
    .stButton>button { background-color: #00ffcc; color: black; border-radius: 8px; font-weight: bold; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_cyber_style()

# --- Bandeau VIDOCQ ---
logo_vidocq = Image.open("logos/vidocq4.png").resize((1400, 500))
st.image(logo_vidocq)
st.markdown("---")

# --- Disposition principale ---
col1, col_graph, col2 = st.columns([4, 8, 4])

# ===============================
# SECTION 1 - Chargement corpus
# ===============================
with col1:
    st.markdown("### 📄 Corpus")
    uploaded_files = st.file_uploader(
        "Chargez vos fichiers `.txt`",
        type="txt",
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.session_state["uploaded_files"] = uploaded_files
    elif "uploaded_files" in st.session_state:
        uploaded_files = st.session_state["uploaded_files"]

index_data = None
if uploaded_files:
    try:
        index_data = index_manager.ensure_indexes(uploaded_files)
        st.session_state["index_data"] = index_data
    except Exception as exc:
        st.error(f"Erreur lors de l'indexation : {exc}")
elif "index_data" in st.session_state:
    index_data = st.session_state["index_data"]

# ===============================
# SECTION 2 - Sélecteurs
# ===============================
with col_graph:
    st.markdown("### 🌐 Visualisation")
    view_mode = st.selectbox(
        "Choisissez la vue :",
        ["Graphe des concepts", "Nuage de mots", "Tables", "Carte des événements"],
    )

concept_to_docs = st.session_state.get("concept_to_docs", {})
stored_keywords_input = st.session_state.get("concept_keywords_input", "")
stored_method = st.session_state.get("search_method", "Recherche exacte")

# ===============================
# SECTION 3 - GRAPHE DES CONCEPTS
# ===============================
if view_mode == "Graphe des concepts":
    with col2:
        st.markdown("### 🔍 Méthode de recherche")
        search_method = st.selectbox(
            "Méthode utilisée :",
            ["Recherche exacte", "Recherche sémantique", "Top recherche sémantique", "Recherche par fréquence"],
            index=["Recherche exacte", "Recherche sémantique", "Top recherche sémantique", "Recherche par fréquence"].index(stored_method)
        )

        with st.form("param_form"):
            threshold = st.session_state.get("threshold", 0.5)
            n_top = st.session_state.get("n_top", 3)

            if search_method == "Recherche sémantique":
                threshold = st.slider("Seuil de similarité", 0.0, 1.0, threshold, step=0.01)
            elif search_method == "Top recherche sémantique":
                n_top = st.number_input(
                    "Nombre de documents à afficher (nœuds du graphe)",
                    min_value=1, max_value=100, value=n_top, step=1
                )
            elif search_method == "Recherche par fréquence":
                threshold = st.slider("Seuil de score TF-IDF", 0.0, 1.0, threshold, step=0.01)

            keywords_input = st.text_input(
                "Entrez les concepts (séparés par des virgules)",
                value=stored_keywords_input,
            )
            submitted = st.form_submit_button("Valider les paramètres")

    if submitted:
        if not index_data:
            st.warning("Veuillez charger des documents avant de lancer l'analyse.")
        elif not keywords_input.strip():
            st.warning("Veuillez saisir au moins un concept.")
        else:
            keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
            if not keywords:
                st.warning("Aucun concept valide détecté.")
            else:
                # --- Sauvegarde des paramètres actifs ---
                st.session_state["search_method"] = search_method
                st.session_state["threshold"] = threshold
                st.session_state["n_top"] = n_top
                st.session_state["concept_keywords_input"] = keywords_input

                # --- Exécution selon la méthode ---
                if search_method == "Recherche exacte":
                    concept_to_docs = extract_exact_concepts(index_data, keywords)
                elif search_method == "Recherche sémantique":
                    concept_to_docs = extract_semantic_concepts(index_data, keywords, threshold or 0.5)
                elif search_method == "Top recherche sémantique":
                    concept_to_docs = extract_top_semantic_concepts(index_data, keywords, int(n_top))
                    for k in concept_to_docs:
                        concept_to_docs[k] = concept_to_docs[k][:n_top]
                else:  # Recherche par fréquence
                    threshold = threshold if threshold > 0 else 0.1
                    concept_to_docs = extract_tfidf_concepts(index_data, keywords, threshold)
                    if not concept_to_docs:
                        concept_to_docs = extract_tfidf_concepts(index_data, keywords, 0.1)

                st.session_state["concept_to_docs"] = concept_to_docs
                st.session_state["concept_keywords"] = keywords
                st.rerun()

# ===============================
# SECTION 4 - AFFICHAGE DU GRAPHE
# ===============================
# ===============================
# SECTION 4 - AFFICHAGE DU GRAPHE
# ===============================
if view_mode == "Graphe des concepts":
    if concept_to_docs:
        G = build_graph(concept_to_docs)

        if len(G.nodes) == 0:
            with col_graph:
                st.error("Aucun nœud dans le graphe. Vérifiez la construction du graphe.")
        else:
            html_path = display_graph(G)

            with col_graph:
                # 🔴 Affichage du nombre de nœuds et arêtes en rouge
                st.markdown(
                    f"<p style='color:blue; font-weight:bold;'>Graphe généré : {len(G.nodes)} nœuds, {len(G.edges)} arêtes</p>",
                    unsafe_allow_html=True
                )

                with open(html_path, "r", encoding="utf-8") as f:
                    components.html(f.read(), height=600)

            # Si aucune arête (relations concept-doc) → message rouge
            if len(G.edges) == 0:
                with col_graph:
                    st.markdown(
                        "<p style='color:red; font-weight:bold;'>⚠️ Aucune relation concept–document pour ce paramétrage (concepts affichés seuls).</p>",
                        unsafe_allow_html=True
                    )
            else:
                linked_docs = sorted({doc for docs in concept_to_docs.values() for doc in docs})
                if linked_docs and index_data is not None:
                    with col2:
                        selected_doc = st.selectbox("📁 Choisissez un document lié :", linked_docs)
                    if selected_doc:
                        st.markdown(
                            f"""
                            <div style='background-color:white; color:black; padding:1em; height:200px; overflow-y:scroll; border-radius:10px;'>
                                <pre style='white-space: pre-wrap; word-wrap: break-word;'>{index_data.documents[selected_doc]}</pre>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

    else:
        # --- Cas où concept_to_docs est vide ---
        has_docs = bool(index_data and getattr(index_data, "documents", None))
        has_keywords = bool(st.session_state.get("concept_keywords_input", "").strip())

        with col_graph:
            if not has_docs or not has_keywords:
                st.markdown(
                    "<p style='color:blue; font-weight:bold;'>⚠️ Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.</p>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<p style='color:blue; font-weight:bold;'>⚠️ Graphe vide pour ce paramétrage (aucune relation trouvée entre concepts et documents).</p>",
                    unsafe_allow_html=True
                )
