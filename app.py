
# -*- coding: utf-8 -*-

############################
# Application              #
#                          #
# Last update : 2025/07/18 #
############################


# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from data_loader import load_documents
from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts, extract_top_semantic_concepts, clean_text, clean_text_light
from graph_builder import build_graph
from graph_display import display_graph, export_graph_image 
from word_cloud_builder import generate_wordcloud
from table_builder import build_event_table
import io
import os
import tempfile
import pandas as pd
from extraction_structuree import extraction_structuree
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import folium
from streamlit_folium import st_folium
from geocodage import geocoder_lieu


# Ton extraction (tu l’as déjà pour "Synthèse")
from extraction_structuree import extraction_structuree


@st.cache_data(show_spinner=True)
def run_extraction_cached(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Exécute extraction_structuree() une seule fois pour un contenu donné.
    Clé du cache = (file_bytes, filename). Si le contenu ne change pas, pas de rerun coûteux.
    """
    suffix = ".txt" if filename.lower().endswith(".txt") else ".txt"
    with tempfile.TemporaryDirectory() as tmpd:
        input_path = os.path.join(tmpd, f"input{suffix}")
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        out_tsv = os.path.join(tmpd, "faits_extraits.tsv")
        checkpoint_tsv = os.path.join(tmpd, "ckpt.tsv")

        df = extraction_structuree(
            nom_fichier=input_path,
            out_tsv=out_tsv,
            checkpoint_tsv=checkpoint_tsv,
            keep_checkpoint=False,
        )
        # On retourne le DataFrame — le TSV disque est éphémère & inutile ici
        return df


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

# Ouvre et redimensionne l’image au format 4:1 (ex. : 1400x350)
logo_vidocq = Image.open("Logos/vidocq4.png")
logo_vidocq_resized = logo_vidocq.resize((1400, 500))  # Largeur 4x plus grande que hauteur

# Affiche dans Streamlit
st.image(logo_vidocq_resized)

st.markdown("---")


# --- Disposition principale ---
col1, col_graph, col2 = st.columns([4, 8, 4])

with col1:
    st.markdown("### 📄 Corpus")
    files = st.file_uploader("Chargez vos fichiers `.txt`", type="txt", accept_multiple_files=True)

with col_graph:
    st.markdown("### 🌐 Visualisation")
    view_mode = st.selectbox("Choisissez la vue :", ["Graphe des concepts", "Nuage de mots", "Synthèse", "Carte"])

# --- Traitement principal ---

# 🔍 Cas Graphe des concepts
if view_mode == "Graphe des concepts":

    with col2:
            
        st.markdown("### 🔍 Méthode de recherche")
        search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Top recherche sémantique", "Recherche par fréquence"])

        with st.form("param_form"):
            threshold = None
            if search_method == "Recherche sémantique":
                threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
            if search_method == "Top recherche sémantique":
                n_top = st.number_input("Nombre de documents à afficher (nœuds du graphe)", min_value=1, max_value=100, value=1, step=1)
            if search_method == "Recherche par fréquence":
                threshold = st.slider("Seuil de score", 0.0, 1.0, 0.5, step=0.01)
            submitted = st.form_submit_button("Valider les paramètres")

            st.markdown("### 💬 Concepts à rechercher")
            keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

    if submitted and keywords_input and files:
    # if keywords_input and files:
        corpus = load_documents(files)
        keywords = [k.strip().lower() for k in keywords_input.split(",")]

        doc_names = list(corpus.keys())
        doc_texts = [corpus[doc] for doc in doc_names]

        st.session_state["corpus"] = corpus
        st.session_state["doc_texts"] = doc_texts

        # Traitement selon méthode choisie
        if search_method == "Recherche exacte":
            concept_to_docs = extract_exact_concepts(corpus, keywords)
        elif search_method == "Recherche sémantique":
            concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold)
        elif search_method == "Top recherche sémantique":
            concept_to_docs = extract_top_semantic_concepts(corpus, keywords, n_top)
        else:
            concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold)

        st.session_state["concept_to_docs"] = concept_to_docs
        st.session_state["filtered"] = concept_to_docs    

# ☁️ Cas Nuage de mots (pas besoin de keywords)
elif view_mode == "Nuage de mots":

    with col2:

        st.markdown("### 🔍 Sélection du document")

        if files:
            corpus = load_documents(files)
            doc_names = list(corpus.keys())
            doc_texts = [corpus[doc] for doc in doc_names]
            selected_doc = st.selectbox("📁 Choisissez un document lié :", doc_names)
            
            st.session_state["corpus"] = corpus
            st.session_state["doc_texts"] = doc_texts

            # 🔧 Curseur pour choisir le nombre de mots à afficher
            max_words = st.slider("🔢 Nombre de mots dans le nuage", min_value=1, max_value=300, value=10, step=1)

            if "corpus" in st.session_state and selected_doc:
                doc_text = st.session_state["corpus"][selected_doc]

                # fig, wc = generate_wordcloud(doc_text)
                fig, wc = generate_wordcloud(doc_text, max_words=max_words)

                with col_graph:
                    st.markdown("### ☁️ Nuage de mots du document")
                    st.pyplot(fig)

                    # 📥 Bouton de téléchargement
                    img_bytes = io.BytesIO()
                    wc.to_image().save(img_bytes, format="PNG")
                    st.download_button(
                        label="💾 Télécharger le nuage en PNG",
                        data=img_bytes.getvalue(),
                        file_name=f"nuage_{selected_doc}.png",
                        mime="image/png"
                    )

elif view_mode == "Synthèse":

    formatted_text = None
    tsv_bytes = None
    tsv_name = None

    with col2:
        if files:
            # Charger la liste de documents
            corpus = load_documents(files)
            st.session_state["corpus"] = corpus
            st.session_state["doc_texts"] = [corpus[doc] for doc in corpus]

            # 1) Sélection du document
            st.markdown("### 🔍 Sélection du document")
            all_doc_names = list(st.session_state["corpus"].keys())
            selected_doc = st.selectbox("📁 Choisissez un document lié :", all_doc_names)

            # 2) Source des événements (uniformisée)

            st.markdown("### 📥 Source des événements")

            key_src_syn = "source_evt_synthese"
            st.session_state.setdefault(key_src_syn, "Extraction mémoire session")

            source_evt = st.radio(
                "Choisissez la source :",
                ["Extraction mémoire session", "Charger un TSV existant", "Calculer extraction"],
                horizontal=False,
                key=key_src_syn  # <- clé dédiée Synthèse
            )     

            df = None
            if selected_doc:
                key_df = f"df_{selected_doc}"
                files_by_name = {f.name: f for f in files}
                up = files_by_name.get(selected_doc)

                if source_evt == "Extraction mémoire session":
                    df = st.session_state.get(key_df)
                    if df is None:
                        st.warning("Aucune extraction mémorisée pour ce document.")
                elif source_evt == "Charger un TSV existant":
                    tsv_file = st.file_uploader("Chargez un fichier .tsv", type=["tsv"], accept_multiple_files=False)
                    if tsv_file is not None:
                        try:
                            df = pd.read_csv(tsv_file, sep="\t", dtype=str, encoding="utf-8")
                            st.session_state[key_df] = df
                            st.success("TSV chargé et mémorisé.")
                        except Exception as e:
                            st.error(f"Impossible de lire le TSV : {e}")
                else:  # "Calculer extraction"
                    if up is None:
                        st.error("Impossible de retrouver le fichier uploadé.")
                    else:
                        file_bytes = up.getvalue()
                        with st.spinner("Extraction des événements en cours..."):
                            df = run_extraction_cached(file_bytes, selected_doc)
                        if df is not None:
                            st.session_state[key_df] = df
                            st.success("Extraction terminée et mémorisée.")

            # 3) Construire et afficher la synthèse
            if df is not None and not df.empty:
                blocs = []
                for _, row in df.iterrows():
                    resume    = str(row.get("resume", "")).strip()
                    lieu      = str(row.get("lieu", "")).strip()
                    moment    = str(row.get("moment", "")).strip()
                    individus = str(row.get("individus", "")).strip()
                    blocs.append("\n".join([
                        f"Événement : {resume}",
                        f"Lieu : {lieu}",
                        f"Moment : {moment}",
                        f"Individus : {individus}",
                    ]))
                formatted_text = "\n\n".join(blocs) if blocs else "Aucun événement détecté."

                # TSV en mémoire pour téléchargement
                import os
                tsv_bytes = df.to_csv(index=False, sep="\t", encoding="utf-8").encode("utf-8")
                tsv_name = f"{os.path.splitext(selected_doc)[0]}_faits.tsv"

    # Affichage central
    if formatted_text is not None:
        with col_graph:
            st.markdown("### Synthèse des événements")
            st.text_area("", formatted_text, height=600, label_visibility="collapsed")

            if tsv_bytes is not None and tsv_name is not None:
                st.download_button(
                    label="💾 Télécharger le TSV des événements",
                    data=tsv_bytes,
                    file_name=tsv_name,
                    mime="text/tab-separated-values",
                )


elif view_mode == "Carte":

    the_map = None

    with col2:
        if files:
            # Charger la liste de documents
            corpus = load_documents(files)
            st.session_state["corpus"] = corpus

            # 1) Sélection du document
            st.markdown("### 🔍 Sélection du document")
            all_doc_names = list(corpus.keys())
            selected_doc = st.selectbox("📁 Choisissez un document lié :", all_doc_names)

            # 2) Source des événements (uniformisée)            
            st.markdown("### 📥 Source des événements")

            key_src_map = "source_evt_carte"
            st.session_state.setdefault(key_src_map, "Extraction mémoire session")

            source_evt = st.radio(
                "Choisissez la source :",
                ["Extraction mémoire session", "Charger un TSV existant", "Calculer extraction"],
                horizontal=False,
                key=key_src_map  # <- clé dédiée Carte
            )
    
            df = None
            if selected_doc:
                key_df = f"df_{selected_doc}"
                files_by_name = {f.name: f for f in files}
                up = files_by_name.get(selected_doc)

                if source_evt == "Extraction mémoire session":
                    df = st.session_state.get(key_df)
                    if df is None:
                        st.warning("Aucune extraction mémorisée pour ce document.")
                elif source_evt == "Charger un TSV existant":
                    tsv_file = st.file_uploader("Chargez un fichier .tsv", type=["tsv"], accept_multiple_files=False)
                    if tsv_file is not None:
                        try:
                            df = pd.read_csv(tsv_file, sep="\t", dtype=str, encoding="utf-8")
                            st.session_state[key_df] = df
                            st.success("TSV chargé et mémorisé.")
                        except Exception as e:
                            st.error(f"Impossible de lire le TSV : {e}")
                else:  # "Calculer extraction"
                    if up is None:
                        st.error("Impossible de retrouver le fichier uploadé.")
                    else:
                        file_bytes = up.getvalue()
                        with st.spinner("Extraction des événements en cours..."):
                            df = run_extraction_cached(file_bytes, selected_doc)
                        if df is not None:
                            st.session_state[key_df] = df
                            st.success("Extraction terminée et mémorisée.")

            # 3) Géocoder et afficher la carte
            if df is not None and not df.empty:
                points = {}  # key: (lat_r, lon_r) -> list of blocs
                for _, row in df.iterrows():
                    lieu = str(row.get("lieu", "")).strip()
                    if not lieu:
                        continue
                    geo = geocoder_lieu(lieu)  # importé de geocodage.py (avec @st.cache_data)
                    if not geo:
                        continue
                    lat, lon, _src = geo
                    key = (round(lat, 5), round(lon, 5))
                    bloc = {
                        "resume": str(row.get("resume", "")).strip(),
                        "lieu": lieu,
                        "moment": str(row.get("moment", "")).strip(),
                        "individus": str(row.get("individus", "")).strip(),
                    }
                    points.setdefault(key, []).append(bloc)

                if not points:
                    st.info("Aucun lieu géocodable (adresse ou ville manquante).")
                else:
                    # Centrer sur le 1er point
                    (lat0, lon0) = list(points.keys())[0]
                    the_map = folium.Map(location=[lat0, lon0], zoom_start=12, tiles="OpenStreetMap")

                    # Marqueurs rouges + popup cumulés
                    for (lat, lon), blocs in points.items():
                        html_blocs = []
                        for b in blocs:
                            html_blocs.append(
                                f"<b>Événement</b> : {b['resume']}<br>"
                                f"<b>Lieu</b> : {b['lieu']}<br>"
                                f"<b>Moment</b> : {b['moment']}<br>"
                                f"<b>Individus</b> : {b['individus']}"
                            )
                        html_popup = "<hr>".join(html_blocs)

                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=6,
                            color="red",
                            fill=True,
                            fill_color="red",
                            fill_opacity=0.9,
                            popup=folium.Popup(html_popup, max_width=350),
                        ).add_to(the_map)

    # Affichage de la carte
    if the_map is not None:
        with col_graph:
            st.markdown("### 🗺️ Carte des événements")
            st_folium(the_map, width=None, height=600)




# --- Affichage du graphe + texte sélectionné ---
if view_mode == "Graphe des concepts":

    if "filtered" in st.session_state:
        G = build_graph(st.session_state["filtered"])
        html_path = display_graph(G)

        with col_graph:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            components.html(html_content, height=600)

            concepts_slug = "_".join([k.strip().lower().replace(" ", "_") for k in keywords_input.split(",")])
            file_name_html = f"graphe_{concepts_slug}.html"
            file_name_png = f"graphe_{concepts_slug}.PNG"

            with open(html_path, "rb") as f:
                st.download_button(
                    label="💾 Télécharger le graphe interactif (.html)",
                    data=f.read(),
                    file_name=file_name_html,
                    mime="text/html"
                )

            # 🔁 Générer l'image statique du graphe
            graph_fig = export_graph_image(G)
            img_buffer = io.BytesIO()
            graph_fig.savefig(img_buffer, format="PNG")

            # 📥 Bouton de téléchargement PNG            
            st.download_button(
                label="🖼️ Télécharger le graphe statique (.png)",
                data=img_buffer.getvalue(),
                file_name=file_name_png,
                mime="image/png"
)

        # ✅ Documents liés uniquement
        linked_docs = sorted(set(doc for docs in st.session_state["filtered"].values() for doc in docs))

        with col2:
            st.markdown("### 💬 Visionnage des documents du graphe")
            selected_doc = st.selectbox("📁 Choisissez un document lié :", linked_docs)

        # with col_graph:
            if selected_doc:
                st.markdown(
                    f"""
                    <div style='background-color:white; color:black; padding:1em; height:200px; overflow-y:scroll; border-radius:10px;'>
                        <pre style='white-space: pre-wrap; word-wrap: break-word;'>{st.session_state["corpus"][selected_doc]}</pre>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        with col_graph:
            st.info("Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.")

