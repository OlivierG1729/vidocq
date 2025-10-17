# -*- coding: utf-8 -*-

############################
# Application              #
#                          #
# Last update : 2025/07/18 #
############################

import io

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

from concept_extractor import (
    extract_exact_concepts,
    extract_semantic_concepts,
    extract_tfidf_concepts,
    extract_top_semantic_concepts,
)
from entity_extractor import get_entity_cache
from graph_builder import build_graph
from graph_display import display_graph, export_graph_image
from lib.indexing import get_index_manager
from word_cloud_builder import generate_wordcloud

index_manager = get_index_manager()
entity_cache = get_entity_cache()

st.set_page_config(layout="wide")


# --- Style cyber ---
def set_cyber_style():
    css = """
    <style>
    # .stApp { background-color: #000c15; color: #00ffcc; font-family: 'Courier New', monospace; }
    .stApp { background: linear-gradient(to bottom, #002a2d, #d2ac7a); color: #00ffcc; font-family: 'Courier New', monospace; }
    # img { box-shadow: 0px 30px 80px -10px rgba(255, 200, 160, 0.5);  /* couleur saumon douce */ border-radius: 10px; }
    # h1,h2,h4,h5,h6 { color: #39ff14; text-shadow: 0 0 5px #39ff14; }
    h1,h2,h3,h4,h5,h6 {
    color: #003300; /* texte vert foncé */
    text-shadow:
        -1px -1px 0 #FFA07A,
            1px -1px 0 #FFA07A,
        -1px  1px 0 #FFA07A,
            1px  1px 0 #FFA07A; /* contour saumon */
    background-color: transparent; /* fond invisible */
    border: none; /* pas de contour */
    padding: 0;
    margin-bottom: 12px; }
    label, .stMarkdown, .stSelectbox { color: #00ffcc !important; }
    .stTextInput input { color: black !important; background-color: white !important; }
    .stButton>button { background-color: #00ffcc; color: black; border-radius: 8px; font-weight: bold; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


set_cyber_style()

# --- Bandeau VIDOCQ ---
logo_vidocq = Image.open("logos/vidocq4.png")
logo_vidocq_resized = logo_vidocq.resize((1400, 500))
st.image(logo_vidocq_resized)

st.markdown("---")

# --- Disposition principale ---
col1, col_graph, col2 = st.columns([4, 8, 4])

with col1:
    st.markdown("### 📄 Corpus")
    uploaded_files = st.file_uploader(
        "Chargez vos fichiers `.txt`",
        type="txt",
        accept_multiple_files=True,
    )

index_data = None
if uploaded_files:
    try:
        index_data = index_manager.ensure_indexes(uploaded_files)
        current_hashes = index_data.document_hashes
        if st.session_state.get("document_hashes") != current_hashes:
            st.session_state["document_hashes"] = current_hashes
            st.session_state.pop("concept_to_docs", None)
            st.session_state.pop("concept_keywords", None)
            st.session_state.pop("concept_keywords_input", None)
    except Exception as exc:  # pragma: no cover - defensive guard for Streamlit
        st.error(f"Erreur lors de l'indexation des documents : {exc}")
else:
    st.session_state.pop("document_hashes", None)

with col_graph:
    st.markdown("### 🌐 Visualisation")
    view_mode = st.selectbox(
        "Choisissez la vue :",
        ["Graphe des concepts", "Nuage de mots", "Tables"],
    )

# --- Traitement principal ---
concept_to_docs = st.session_state.get("concept_to_docs")
stored_keywords_input = st.session_state.get("concept_keywords_input", "")

if view_mode == "Graphe des concepts":
    with col2:
        st.markdown("### 🔍 Méthode de recherche")
        search_method = st.selectbox(
            "Méthode utilisée :",
            [
                "Recherche exacte",
                "Recherche sémantique",
                "Top recherche sémantique",
                "Recherche par fréquence",
            ],
        )

        with st.form("param_form"):
            threshold = None
            n_top = 3
            if search_method == "Recherche sémantique":
                threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
            if search_method == "Top recherche sémantique":
                n_top = st.number_input(
                    "Nombre de documents à afficher (nœuds du graphe)",
                    min_value=1,
                    max_value=100,
                    value=3,
                    step=1,
                )
            if search_method == "Recherche par fréquence":
                threshold = st.slider("Seuil de score", 0.0, 1.0, 0.5, step=0.01)

            keywords_input = st.text_input(
                "Entrez les concepts (séparés par des virgules)",
                value=stored_keywords_input,
            )
            submitted = st.form_submit_button("Valider les paramètres")

    if submitted:
        if not uploaded_files:
            st.warning("Veuillez charger des documents avant de lancer l'analyse.")
        elif not keywords_input.strip():
            st.warning("Veuillez saisir au moins un concept.")
        else:
            keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
            if not keywords:
                st.warning("Aucun concept valide détecté.")
            elif index_data is None:
                st.error("Impossible d'accéder aux index : merci de réessayer.")
            else:
                if search_method == "Recherche exacte":
                    concept_to_docs = extract_exact_concepts(index_data, keywords)
                elif search_method == "Recherche sémantique":
                    concept_to_docs = extract_semantic_concepts(index_data, keywords, threshold or 0.5)
                elif search_method == "Top recherche sémantique":
                    concept_to_docs = extract_top_semantic_concepts(index_data, keywords, int(n_top))
                else:
                    concept_to_docs = extract_tfidf_concepts(index_data, keywords, threshold or 0.3)

                st.session_state["concept_to_docs"] = concept_to_docs
                st.session_state["concept_keywords"] = keywords
                st.session_state["concept_keywords_input"] = keywords_input

elif view_mode == "Nuage de mots":
    with col2:
        st.markdown("### 🔍 Sélection du document")
        if not uploaded_files:
            st.info("Chargez des documents pour générer un nuage de mots.")
        elif index_data is None:
            st.error("Impossible de récupérer les documents indexés.")
        else:
            doc_names = index_data.doc_order
            selected_doc = st.selectbox("📁 Choisissez un document lié :", doc_names)
            max_words = st.slider(
                "🔢 Nombre de mots dans le nuage",
                min_value=1,
                max_value=300,
                value=50,
                step=1,
            )

            if selected_doc:
                doc_text = index_data.documents[selected_doc]
                fig, wc = generate_wordcloud(doc_text, max_words=max_words)

                with col_graph:
                    st.markdown("### ☁️ Nuage de mots du document")
                    st.pyplot(fig)

                    img_bytes = io.BytesIO()
                    wc.to_image().save(img_bytes, format="PNG")
                    st.download_button(
                        label="💾 Télécharger le nuage en PNG",
                        data=img_bytes.getvalue(),
                        file_name=f"nuage_{selected_doc}.png",
                        mime="image/png",
                    )

elif view_mode == "Tables":
    with col2:
        st.markdown("### 🔍 Eléments observés")
        if not uploaded_files:
            st.info("Chargez des documents pour consulter les tableaux d'entités.")
        elif index_data is None:
            st.error("Impossible de récupérer les documents indexés.")
        else:
            doc_names = index_data.doc_order
            selected_docs = st.multiselect("Choisissez un ou plusieurs documents :", doc_names)

            if selected_docs:
                for doc_name in selected_docs:
                    cached = entity_cache.get_or_create(
                        doc_name,
                        index_data.document_hashes.get(doc_name, ""),
                        index_data.documents[doc_name],
                    )
                    table = pd.DataFrame(
                        {
                            "Individus": [", ".join(cached.get("individuals", [])) or "—"],
                            "Lieux": [", ".join(cached.get("locations", [])) or "—"],
                            "Adresses": [", ".join(cached.get("addresses", [])) or "—"],
                            "Dates": [", ".join(cached.get("dates", [])) or "—"],
                            "Horaires": [", ".join(cached.get("times", [])) or "—"],
                            "Résumé": [cached.get("summary") or "—"],
                        }
                    ).T
                    table.columns = [doc_name]

                    st.markdown(f"#### {doc_name}")
                    st.table(table)

# --- Affichage du graphe + texte sélectionné ---
if view_mode == "Graphe des concepts":
    if concept_to_docs:
        G = build_graph(concept_to_docs)
        html_path = display_graph(G)

        with col_graph:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            components.html(html_content, height=600)

            keywords_value = st.session_state.get("concept_keywords_input", "")
            concepts_slug = "_".join(
                [k.strip().lower().replace(" ", "_") for k in keywords_value.split(",") if k.strip()]
            )
            file_name_html = f"graphe_{concepts_slug or 'concepts'}.html"
            file_name_png = f"graphe_{concepts_slug or 'concepts'}.png"

            with open(html_path, "rb") as f:
                st.download_button(
                    label="💾 Télécharger le graphe interactif (.html)",
                    data=f.read(),
                    file_name=file_name_html,
                    mime="text/html",
                )

            graph_fig = export_graph_image(G)
            img_buffer = io.BytesIO()
            graph_fig.savefig(img_buffer, format="PNG")

            st.download_button(
                label="🖼️ Télécharger le graphe statique (.png)",
                data=img_buffer.getvalue(),
                file_name=file_name_png,
                mime="image/png",
            )

        linked_docs = sorted({doc for docs in concept_to_docs.values() for doc in docs})

        if linked_docs and index_data is not None:
            with col2:
                st.markdown("### 💬 Visionnage des documents du graphe")
                selected_doc = st.selectbox("📁 Choisissez un document lié :", linked_docs)

            if selected_doc:
                st.markdown(
                    """
                    <div style='background-color:white; color:black; padding:1em; height:200px; overflow-y:scroll; border-radius:10px;'>
                        <pre style='white-space: pre-wrap; word-wrap: break-word;'>%s</pre>
                    </div>
                    """
                    % index_data.documents[selected_doc],
                    unsafe_allow_html=True,
                )
    else:
        with col_graph:
            st.info("Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.")
