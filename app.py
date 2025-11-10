# -*- coding: utf-8 -*-

############################
# Application              #
#                          #
# Last update : 2025/11/10 #
############################

import io
import os
import time
import tempfile
import pandas as pd
from PIL import Image

import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium
import folium  # ← fallback sécurisé si besoin
import pydeck as pdk
import json

from data_loader import load_documents
from concept_extractor import (
    extract_exact_concepts, extract_tfidf_concepts,
    extract_semantic_concepts, extract_top_semantic_concepts,
    clean_text, clean_text_light
)
from graph_builder import build_graph
from graph_display import display_graph, export_graph_image
from word_cloud_builder import generate_wordcloud
from table_builder import build_event_table
from extraction_structuree import extraction_structuree
from geocodage import geocoder_lieu
from mapping_chrono import (
    preprocess_events_global,
    preprocess_events_by_individual,
    build_map_static,   # (toujours disponible si besoin du fallback Folium)
)

# ✅ AJOUT VIDOCQ : extraction procédures
from extraction_procedure import extraction_procedure


mode_visu = "Statique"  # temporaire, dynamique désactivée pour l'instant

# ====================================
# CACHES & CONFIG
# ====================================

@st.cache_data(show_spinner=True)
def run_extraction_cached(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Exécute extraction_structuree() une seule fois pour un contenu donné.
    Clé du cache = (file_bytes, filename).
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
        return df

st.set_page_config(layout="wide")

def set_cyber_style():
    css = """
    <style>
    .stApp { background: linear-gradient(to bottom, #002a2d, #d2ac7a); color: #00ffcc; font-family: 'Courier New', monospace; }
    h1,h2,h3,h4,h5,h6 {
      color: #003300;
      text-shadow:
        -1px -1px 0 #FFA07A,
         1px -1px 0 #FFA07A,
        -1px  1px 0 #FFA07A,
         1px  1px 0 #FFA07A;
      background-color: transparent;
      border: none;
      padding: 0;
      margin-bottom: 12px;
    }
    label, .stMarkdown, .stSelectbox { color: #00ffcc !important; }
    .stTextInput input { color: black !important; background-color: white !important; }
    .stButton>button { background-color: #00ffcc; color: black; border-radius: 8px; font-weight: bold; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_cyber_style()

# ====================================
# LOGO & LAYOUT
# ====================================

try:
    logo_vidocq = Image.open("Logos/vidocq4.png")
    logo_vidocq_resized = logo_vidocq.resize((1400, 500))
    st.image(logo_vidocq_resized)
except Exception:
    st.info("Logo introuvable (Logos/vidocq4.png).")
st.markdown("---")

col1, col_graph, col2 = st.columns([4, 8, 4])

with col1:
    st.markdown("### 📄 Corpus")
    # ✅ AJOUT VIDOCQ : prise en charge des formats .odt/.doc/.docx
    files = st.file_uploader(
        "Chargez vos fichiers (`.txt`, `.odt`, `.doc`, `.docx`)",
        type=["txt", "odt", "doc", "docx"],
        accept_multiple_files=True
    )

with col_graph:
    st.markdown("### 🌐 Visualisation")
    # ✅ AJOUT VIDOCQ : ajout de la vue “Extractions informations procédure”
    view_mode = st.selectbox(
        "Choisissez la vue :",
        ["Graphe des concepts", "Nuage de mots", "Synthèse", "Carte", "Extractions informations procédure"]
    )

# ====================================
# ETAT : LANCEMENT MANUEL + “DIRTY” OPTIONS
# ====================================

# Flags de lancement par vue
if "launch_flags" not in st.session_state:
    st.session_state["launch_flags"] = {
        "Synthèse": False,
        "Carte": False,
        "Nuage de mots": False,
        "Graphe des concepts": False,
        # ✅ AJOUT VIDOCQ : ajout du flag pour la nouvelle vue
        "Extractions informations procédure": False,
    }

# Dernières options vues (pour détecter les changements)
if "last_opts" not in st.session_state:
    st.session_state["last_opts"] = {}

def _list_file_names(_files):
    if not _files:
        return []
    return [getattr(f, "name", f"{i}.txt") for i, f in enumerate(_files)]

def _mark_dirty_if_options_changed(view_name: str, **opts):
    """
    Compare l'état courant des options à l'état mémorisé.
    Si différent → marque la vue comme “non lancée” (il faudra recliquer).
    """
    prev = st.session_state["last_opts"].get(view_name)
    if prev != opts:
        st.session_state["last_opts"][view_name] = opts
        st.session_state["launch_flags"][view_name] = False

def launch_view(view_name: str):
    # Option : ne pas éteindre les autres vues (mais ici on garde exclusif)
    for k in st.session_state["launch_flags"]:
        st.session_state["launch_flags"][k] = False
    st.session_state["launch_flags"][view_name] = True

# ====================================
# HELPERS
# ====================================

def _list_individus(df_: pd.DataFrame):
    s = set()
    if "individus" not in df_.columns:
        return []
    for val in df_["individus"]:
        for p in str(val).split(";"):
            p = p.strip()
            if p:
                s.add(p)
    return sorted(s)

# ---- Styles Mapbox disponibles ----
MAPBOX_STYLE_OPTIONS = {
    "Clair": "mapbox://styles/mapbox/light-v11",
    "Sombre": "mapbox://styles/mapbox/dark-v11",
    "Extérieur": "mapbox://styles/mapbox/outdoors-v12",
    "Satellite": "mapbox://styles/mapbox/satellite-streets-v12",
}

def _get_mapbox_style(selected_style_uri: str | None = None):
    """
    Si une clé Mapbox est disponible (st.secrets ou variable d'env),
    fixe MAPBOX_API_KEY dans os.environ (requis par pydeck) et renvoie
    l'URI de style choisi. Sinon, renvoie None (fond neutre).
    """
    token = None
    try:
        token = st.secrets.get("MAPBOX_API_KEY")
    except Exception:
        pass
    token = token or os.environ.get("MAPBOX_API_KEY")
    if token:
        os.environ["MAPBOX_API_KEY"] = token
        return selected_style_uri or "mapbox://styles/mapbox/light-v11"
    return None

@st.cache_data
def geocode_cached(lieu: str):
    """
    Géocode un lieu une seule fois et conserve le résultat
    dans le cache Streamlit.
    Cela évite les appels répétés à l'API pour les mêmes lieux.
    """
    return geocoder_lieu(lieu)

@st.cache_data
def build_points_df_cached(events_key: str, events: list, _geocoder_lieu):
    """
    Construit un DataFrame pydeck regroupé par coordonnées géographiques.
    Si plusieurs événements partagent le même lieu (lat, lon), ils sont fusionnés
    dans une même ligne, et les événements sont triés par ordre chronologique
    si possible (selon la colonne 'moment').
    Le géocodage est mis en cache pour éviter les répétitions coûteuses.
    """
    import time
    t0 = time.perf_counter()
    rows = []
    for i, ev in enumerate(events, start=1):
        lieu = (ev.get("lieu") or "").strip()
        if not lieu:
            continue

        g = geocode_cached(lieu)
        if not g:
            continue

        lat, lon, _ = g
        rows.append({
            "lat": lat,
            "lon": lon,
            "resume": ev.get("resume", ""),
            "lieu": lieu,
            "moment": ev.get("moment", ""),
            "individus": ev.get("individus", ""),
        })

    if not rows:
        return pd.DataFrame(columns=["lat", "lon", "resume", "lieu", "moment", "individus", "tooltip"])

    df = pd.DataFrame(rows)

    def _parse_moment_to_sortkey(moment):
        import re
        import datetime
        moment = str(moment).strip()
        if not moment:
            return datetime.datetime.max
        try:
            date_match = re.search(r"(\d{1,2} [A-Za-zéû]+\s*\d{4})", moment)
            if date_match:
                try:
                    return datetime.datetime.strptime(date_match.group(1), "%d %B %Y")
                except Exception:
                    pass
            date_iso = re.search(r"(\d{4}-\d{2}-\d{2})", moment)
            if date_iso:
                return datetime.datetime.strptime(date_iso.group(1), "%Y-%m-%d")
        except Exception:
            pass
        return datetime.datetime.max

    df["sortkey"] = df["moment"].apply(_parse_moment_to_sortkey)
    df = df.sort_values(["lat", "lon", "sortkey"], ascending=True)

    grouped = []
    for (lat, lon, lieu), grp in df.groupby(["lat", "lon", "lieu"]):
        resumes = [r for r in grp["resume"] if r]
        moments = [m for m in grp["moment"] if m]
        individus = [i for i in grp["individus"] if i]

        tooltip_html = f"<div style='max-height:300px; overflow-y:auto; padding:4px;'>"
        tooltip_html += f"<b>Lieu :</b> {lieu}<br/><hr style='border:0.5px solid #999;'/>"

        max_len = max(len(resumes), len(moments), len(individus))
        for k in range(max_len):
            r = resumes[k] if k < len(resumes) else ""
            m = moments[k] if k < len(moments) else ""
            i = individus[k] if k < len(individus) else ""
            tooltip_html += (
                f"<b>Événement {k+1} :</b> {r}<br/>"
                f"<b>Moment :</b> {m}<br/>"
                f"<b>Individus :</b> {i}<br/><br/>"
            )
        tooltip_html += "</div>"

        grouped.append({
            "lat": lat,
            "lon": lon,
            "lieu": lieu,
            "resume": "; ".join(resumes),
            "moment": "; ".join(moments),
            "individus": "; ".join(individus),
            "tooltip": tooltip_html,
        })

    grouped_df = pd.DataFrame(grouped)
    grouped_df["idx"] = range(1, len(grouped_df) + 1)

    t1 = time.perf_counter()
    print(f"⏱ build_points_df_cached exécuté en {t1 - t0:.2f} s ({len(grouped_df)} points, {len(df)} événements)")

    return grouped_df


def _build_pydeck_dynamic_from_df(
    df_points: pd.DataFrame,
    idx_zero_based: int,
    center: tuple[float,float],
    zoom: int,
    selected_style_uri: str | None
):
    if df_points.empty:
        return None

    current_pos = idx_zero_based + 1
    max_idx = int(df_points["idx"].max())
    if current_pos > max_idx:
        current_pos = 1

    df_points = df_points.copy()
    df_points["is_current"] = (df_points["idx"] == current_pos)

    view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=int(zoom), bearing=0, pitch=0)

    layer_base = pdk.Layer(
        "ScatterplotLayer",
        data=df_points,
        get_position='[lon, lat]',
        get_radius=50,
        radius_min_pixels=3,
        radius_max_pixels=30,
        stroked=True,
        get_line_color=[0, 0, 0, 160],
        line_width_min_pixels=1,
        get_fill_color=[120, 120, 120, 180],
        pickable=True,
    )

    layer_current = pdk.Layer(
        "ScatterplotLayer",
        data=df_points[df_points["is_current"]],
        get_position='[lon, lat]',
        get_radius=140,
        radius_min_pixels=6,
        radius_max_pixels=60,
        stroked=True,
        get_line_color=[0, 0, 0, 200],
        line_width_min_pixels=1,
        get_fill_color=[220, 20, 60, 230],
        pickable=True,
    )

    tooltip = {
        "html": "{tooltip}",
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "maxHeight": "300px",
            "overflowY": "auto",
            "padding": "6px",
            "width": "300px",
            "fontSize": "12px"
        }
    }

    return pdk.Deck(
        layers=[layer_base, layer_current],
        initial_view_state=view_state,
        map_style=_get_mapbox_style(selected_style_uri),
        tooltip=tooltip,
    )

def _fallback_folium_map_from_events(events: list) -> folium.Map:
    coords = []
    for ev in events or []:
        lieu = (ev.get("lieu") or "").strip()
        if not lieu:
            continue
        g = geocoder_lieu(lieu)
        if g:
            lat, lon, _ = g
            coords.append((lat, lon))

    if coords:
        lat_c = sum(lat for lat, _ in coords) / len(coords)
        lon_c = sum(lon for _, lon in coords) / len(coords)
        c = (lat_c, lon_c)
    else:
        c = (48.8566, 2.3522)

    m = folium.Map(location=c, zoom_start=12, control_scale=True, tiles="OpenStreetMap")
    if coords:
        for lat, lon in coords:
            folium.CircleMarker(location=(lat, lon), radius=5, fill=True).add_to(m)
    else:
        folium.Marker(location=c, tooltip="Aucune donnée", popup="Aucune donnée à afficher").add_to(m)

    folium.LayerControl().add_to(m)
    return m

# ====================================
# ✅ AJOUT VIDOCQ : utilitaire conversion procédures
# ====================================

def ensure_procedure_jsons(files, work_dir):
    """
    Vérifie pour chaque fichier procédure s'il existe un JSON correspondant.
    Sinon, le génère automatiquement avec extraction_procedure().
    """
    json_paths = []
    for f in files:
        base_name, ext = os.path.splitext(f.name)
        json_path = os.path.join(work_dir, f"{base_name}.json")
        if not os.path.exists(json_path):
            tmp_path = os.path.join(work_dir, f.name)
            with open(tmp_path, "wb") as tmp:
                tmp.write(f.read())
            extraction_procedure(tmp_path, out_json=json_path)
        json_paths.append(json_path)
    return json_paths


# ====================================
# VUES
# ====================================


# 🔍 GRAPHE DES CONCEPTS
if view_mode == "Graphe des concepts":
    with col2:
        st.markdown("### ⚙️ Paramètres et options")
        search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Top recherche sémantique", "Recherche par fréquence"])

        # Paramètres
        threshold, n_top = None, None
        if search_method == "Recherche sémantique":
            threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
        elif search_method == "Top recherche sémantique":
            n_top = st.number_input("Nombre de documents par concept", min_value=1, max_value=100, value=1, step=1)
        elif search_method == "Recherche par fréquence":
            threshold = st.slider("Seuil de score", 0.0, 1.0, 0.5, step=0.01)

        keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

        # Marque la vue "dirty" si options changent
        _mark_dirty_if_options_changed(
            "Graphe des concepts",
            files=_list_file_names(files),
            search_method=search_method,
            threshold=threshold,
            n_top=n_top,
            keywords=keywords_input,
        )

        # Bouton de lancement
        launch_btn = st.button("🚀 Lancer la vue", key="btn_graphe")
        if launch_btn:
            launch_view("Graphe des concepts")

    if st.session_state["launch_flags"]["Graphe des concepts"]:
        if keywords_input and files:
            corpus = load_documents(files)
            keywords = [k.strip().lower() for k in keywords_input.split(",")]
            doc_names = list(corpus.keys())
            doc_texts = [corpus[doc] for doc in doc_names]

            st.session_state["corpus"] = corpus
            st.session_state["doc_texts"] = doc_texts
            st.session_state["last_keywords"] = keywords_input

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

            G = build_graph(st.session_state["filtered"])
            html_path = display_graph(G)

            with col_graph:
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                components.html(html_content, height=600)

                concepts_slug = "_".join([k.strip().lower().replace(" ", "_")
                                          for k in (st.session_state.get("last_keywords","") or "").split(",")]) if "last_keywords" in st.session_state else "concepts"
                file_name_html = f"graphe_{concepts_slug}.html"
                file_name_png = f"graphe_{concepts_slug}.PNG"

                with open(html_path, "rb") as f:
                    st.download_button(
                        label="💾 Télécharger le graphe interactif (.html)",
                        data=f.read(),
                        file_name=file_name_html,
                        mime="text/html"
                    )

                graph_fig = export_graph_image(G)
                img_buffer = io.BytesIO()
                graph_fig.savefig(img_buffer, format="PNG")
                st.download_button(
                    label="🖼️ Télécharger le graphe statique (.png)",
                    data=img_buffer.getvalue(),
                    file_name=file_name_png,
                    mime="image/png"
                )

            linked_docs = sorted(set(doc for docs in st.session_state["filtered"].values() for doc in docs))

            with col2:
                selected_doc = st.selectbox("📁 Choisissez un document lié :", linked_docs, key="doc_graphe_view")

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
                st.info("Veuillez charger des documents, entrer des concepts, puis cliquer sur 🚀 **Lancer la vue**.")

# ☁️ NUAGE DE MOTS
elif view_mode == "Nuage de mots":
    with col2:
        st.markdown("### ⚙️ Paramètres et options")
        if files:
            corpus = load_documents(files)
            doc_names = list(corpus.keys())
            doc_texts = [corpus[doc] for doc in doc_names]
            selected_doc = st.selectbox("📁 Choisissez un document lié :", doc_names, key="doc_nuage")
            st.session_state["corpus"] = corpus
            st.session_state["doc_texts"] = doc_texts

            max_words = st.slider("🔢 Nombre de mots dans le nuage", min_value=1, max_value=300, value=10, step=1, key="nuage_maxw")

            # Marquer dirty
            _mark_dirty_if_options_changed(
                "Nuage de mots",
                files=_list_file_names(files),
                selected_doc=selected_doc,
                max_words=max_words,
            )

            launch_btn = st.button("🚀 Lancer la vue", key="btn_nuage")
            if launch_btn:
                launch_view("Nuage de mots")

    if st.session_state["launch_flags"]["Nuage de mots"]:
        if "corpus" in st.session_state and st.session_state.get("corpus") and st.session_state.get("doc_texts"):
            doc_text = st.session_state["corpus"][selected_doc]
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
                    mime="image/png"
                )
        else:
            with col_graph:
                st.info("Veuillez charger des documents puis cliquer sur 🚀 **Lancer la vue**.")

# 🧾 SYNTHÈSE
elif view_mode == "Synthèse":
    formatted_text = None
    tsv_bytes = None
    tsv_name = None

    with col2:
        st.markdown("### ⚙️ Paramètres et options")
        if files:
            corpus = load_documents(files)
            st.session_state["corpus"] = corpus
            st.session_state["doc_texts"] = [corpus[doc] for doc in corpus]

            all_doc_names = list(st.session_state["corpus"].keys())
            selected_doc = st.selectbox("📁 Choisissez un document lié :", all_doc_names, key="doc_syn")

           # 📥 Source des événements
            key_src_syn = "source_evt_synthese"
            st.session_state.setdefault(key_src_syn, "Calculer extraction depuis document")
            source_evt = st.selectbox(
                "Source :",
                ["Calculer extraction depuis document", "Calculer extraction depuis un TSV"],
                key=key_src_syn
            )


            # Marquer dirty si options changent
            _mark_dirty_if_options_changed(
                "Synthèse",
                files=_list_file_names(files),
                selected_doc=selected_doc,
                source_evt=source_evt,
            )

            # Bouton de lancement
            launch_btn = st.button("🚀 Lancer la vue", key="btn_syn")
            if launch_btn:
                launch_view("Synthèse")

            # Préparation des données (SEULEMENT après lancement)
            if st.session_state["launch_flags"]["Synthèse"]:
                df = None
                if selected_doc:
                    key_df = f"df_{selected_doc}"
                    files_by_name = {f.name: f for f in files}
                    up = files_by_name.get(selected_doc)



                    if source_evt == "Calculer extraction depuis document":
                        df = st.session_state.get(key_df)
                        if df is None:
                            if up is None:
                                st.error("Impossible de retrouver le fichier uploadé.")
                            else:
                                file_bytes = up.getvalue()
                                with st.spinner("Extraction des événements en cours..."):
                                    df = run_extraction_cached(file_bytes, selected_doc)
                                if df is not None:
                                    st.session_state[key_df] = df
                                    st.success("Extraction terminée et mémorisée.")
                    elif source_evt == "Calculer extraction depuis un TSV":
                        tsv_file = st.file_uploader("Chargez un fichier .tsv", type=["tsv"], accept_multiple_files=False, key="tsv_syn")
                        if tsv_file is not None:
                            try:
                                df = pd.read_csv(tsv_file, sep="\t", dtype=str, encoding="utf-8")
                                st.session_state[key_df] = df
                                st.success("TSV chargé et mémorisé.")
                            except Exception as e:
                                st.error(f"Impossible de lire le TSV : {e}")
                    

                # Construction du rendu uniquement si df disponible
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

                    tsv_bytes = df.to_csv(index=False, sep="\t", encoding="utf-8").encode("utf-8")
                    tsv_name = f"{os.path.splitext(selected_doc)[0]}_faits.tsv"

    # Affichage après lancement
    if st.session_state["launch_flags"]["Synthèse"] and (formatted_text is not None):
        with col_graph:
            st.markdown("### Synthèse des événements")

            # 🔹 Clés de session
            key_txt = f"edited_text_{selected_doc}"
            key_df = f"df_{selected_doc}"

            # 🔹 Charger le texte sauvegardé précédemment (ou celui calculé)
            current_text = st.session_state.get(key_txt, formatted_text)

            # 🔹 Zone de texte éditable
            edited_text = st.text_area(
                "",
                value=current_text,
                height=600,
                label_visibility="collapsed",
                key=f"textarea_{selected_doc}",
            )

            # 🔹 Fonction de parsing du texte libre en DataFrame
            def parse_text_to_df(text):
                import re
                blocs = re.split(r"\n\s*\n", text.strip())
                rows = []
                for bloc in blocs:
                    resume, lieu, moment, individus = "", "", "", ""
                    for line in bloc.split("\n"):
                        if line.lower().startswith("événement"):
                            resume = line.split(":", 1)[-1].strip()
                        elif line.lower().startswith("lieu"):
                            lieu = line.split(":", 1)[-1].strip()
                        elif line.lower().startswith("moment"):
                            moment = line.split(":", 1)[-1].strip()
                        elif line.lower().startswith("individus"):
                            individus = line.split(":", 1)[-1].strip()
                    if any([resume, lieu, moment, individus]):
                        rows.append({
                            "resume": resume,
                            "lieu": lieu,
                            "moment": moment,
                            "individus": individus,
                        })
                return pd.DataFrame(rows)

            # 🔹 Bouton de sauvegarde (texte + DataFrame synchronisé)
            if st.button("💾 Sauvegarder les modifications", key=f"save_{selected_doc}"):
                st.session_state[key_txt] = edited_text
                try:
                    new_df = parse_text_to_df(edited_text)
                    if not new_df.empty:
                        st.session_state[key_df] = new_df  # ✅ remplacera le DataFrame existant
                        st.success("Modifications sauvegardées et synchronisées avec la carte.")
                    else:
                        st.warning("Le texte semble vide ou mal formaté — impossible de mettre à jour le DataFrame.")
                except Exception as e:
                    st.error(f"Erreur lors de la mise à jour du DataFrame : {e}")

            # 🔹 Petit texte explicatif
            st.markdown(
                "<p style='color:black; font-size:13px;'>Vous pouvez modifier ce fichier descriptif des événements et enregistrer ces modifications. Ces changements seront visibles dans la carte des événements.</p>",
                unsafe_allow_html=True,
            )

            # 🔹 Téléchargement TSV (inchangé)
            if tsv_bytes is not None and tsv_name is not None:
                st.download_button(
                    label="💾 Télécharger le TSV des événements",
                    data=tsv_bytes,
                    file_name=tsv_name,
                    mime="text/tab-separated-values",
                )

    elif view_mode == "Synthèse":
        with col_graph:
            st.info("Réglez les options puis cliquez sur 🚀 **Lancer la vue** pour afficher la synthèse.")

# 🗺️ CARTE
elif view_mode == "Carte":

    the_map = None
    selected_person = ""

    with col2:
        st.markdown("### ⚙️ Paramètres et options")
        if files:
            corpus = load_documents(files)
            st.session_state["corpus"] = corpus

            all_doc_names = list(corpus.keys())
            selected_doc = st.selectbox("📁 Choisissez un document lié :", all_doc_names, key="doc_map")

           # 📥 Source des événements
            key_src_map = "source_evt_carte"
            st.session_state.setdefault(key_src_map, "Calculer extraction depuis document")
            source_evt = st.selectbox(
                "Source :",
                ["Calculer extraction depuis document", "Calculer extraction depuis un TSV"],
                key=key_src_map
            )

                   


            # 🧭 Mode d’affichage
            key_mode_map = "mode_carte"
            st.session_state.setdefault(key_mode_map, "Trajectoire globale")
            mode_affichage = st.selectbox(
                "Mode :",
                ["Trajectoire globale", "Trajectoires par individu"],
                key=key_mode_map,
            )

            # 🎬 Visualisation
            # key_visu_map = "visu_carte"
            # st.session_state.setdefault(key_visu_map, "Statique")
            # mode_visu = st.selectbox(
            #     "Type d’affichage :",
            #     ["Statique", "Dynamique"],
            #     key=key_visu_map,
            # )

            # 🎨 Style de la carte — APPARAÎT ICI (à droite) ET S'APPLIQUE AUX 2 MODES
            key_style_map = "style_carte"
            st.session_state.setdefault(key_style_map, "Clair")
            style_choice = st.selectbox(
                "Style :",
                list(MAPBOX_STYLE_OPTIONS.keys()),
                key=key_style_map
            )
            selected_style_uri = MAPBOX_STYLE_OPTIONS.get(style_choice, MAPBOX_STYLE_OPTIONS["Clair"])

            # Marque dirty si options changent
            _mark_dirty_if_options_changed(
                "Carte",
                files=_list_file_names(files),
                selected_doc=selected_doc,
                source_evt=source_evt,
                mode_affichage=mode_affichage,
                mode_visu=mode_visu,
                style_choice=style_choice,
            )

            # Bouton de lancement
            launch_btn = st.button("🚀 Lancer la vue", key="btn_carte")
            if launch_btn:
                launch_view("Carte")

            # Préparation des données (SEULEMENT après lancement)
            df = None
            if st.session_state["launch_flags"]["Carte"]:
                if selected_doc:
                    key_df = f"df_{selected_doc}"
                    files_by_name = {f.name: f for f in files}
                    up = files_by_name.get(selected_doc)

                    if source_evt == "Calculer extraction depuis document":
                        df = st.session_state.get(key_df)
                        if df is None:
                            if up is None:
                                st.error("Impossible de retrouver le fichier uploadé.")
                            else:
                                file_bytes = up.getvalue()
                                with st.spinner("Extraction des événements en cours..."):
                                    df = run_extraction_cached(file_bytes, selected_doc)
                                if df is not None:
                                    st.session_state[key_df] = df
                                    st.success("Extraction terminée et mémorisée.")
                    elif source_evt == "Calculer extraction depuis un TSV":
                        tsv_file = st.file_uploader("Chargez un fichier .tsv", type=["tsv"], accept_multiple_files=False, key="tsv_map")
                        if tsv_file is not None:
                            try:
                                df = pd.read_csv(tsv_file, sep="\t", dtype=str, encoding="utf-8")
                                st.session_state[key_df] = df
                                st.success("TSV chargé et mémorisé.")
                            except Exception as e:
                                st.error(f"Impossible de lire le TSV : {e}")               

                  

            # Construction / affichage de la carte APRES lancement
            if st.session_state["launch_flags"]["Carte"]:
                if df is None:
                    st.info("Aucune donnée d'événements pour ce document (choisissez une autre source ou lancez l'extraction).")
                    the_map = None
                elif df.empty:
                    st.info("Le DataFrame d'événements est vide.")
                    the_map = None
                else:
                    # Préparer les événements (globaux ou individuels)
                    if mode_affichage == "Trajectoire globale":
                        events = preprocess_events_global(df)
                        idx_key = f"idx_dyn_{selected_doc}_global"
                        selected_person = ""
                    else:
                        all_inds = _list_individus(df)
                        if not all_inds:
                            st.info("Aucun individu détecté dans ce document.")
                            events = []
                            idx_key = f"idx_dyn_{selected_doc}_none"
                            selected_person = ""
                        else:
                            selected_person = st.selectbox("👤 Sélectionnez un individu :", all_inds, key=f"indiv_{selected_doc}")
                            events = preprocess_events_by_individual(df, selected_person)
                            idx_key = f"idx_dyn_{selected_doc}_{selected_person}"

                    # --- STATIQUE (PyDeck fluide) ---
                    
                    if mode_visu == "Statique":
                        events_key = f"{selected_doc}|{mode_affichage}|{selected_person}|{len(events)}"
                        df_points = build_points_df_cached(events_key, events, geocoder_lieu)

                        if df_points.empty:
                            st.info("Aucun événement géocodable trouvé.")
                            the_map = None
                        else:
                            lat_c = df_points["lat"].mean()
                            lon_c = df_points["lon"].mean()

                            view_state = pdk.ViewState(
                                latitude=lat_c,
                                longitude=lon_c,
                                zoom=10,
                                pitch=0,
                            )

                            layer_points = pdk.Layer(
                                "ScatterplotLayer",
                                data=df_points,
                                get_position='[lon, lat]',
                                get_fill_color='[220, 20, 60, 230]',  # rouge
                                get_radius=120,
                                radius_min_pixels=4,
                                radius_max_pixels=40,
                                pickable=True,
                            )

                            tooltip = {
                                "html": "<b>#{idx}</b><br/><b>Événement:</b> {resume}<br/><b>Lieu:</b> {lieu}<br/><b>Moment:</b> {moment}<br/><b>Individus:</b> {individus}",
                                "style": {"backgroundColor": "white", "color": "black"}
                            }

                            # Style Mapbox sélectionné (appliqué ici)
                            map_style = _get_mapbox_style(selected_style_uri)

                            deck = pdk.Deck(
                                layers=[layer_points],
                                initial_view_state=view_state,
                                map_style=map_style,
                                tooltip=tooltip,
                            )

                            with col_graph:
                                st.markdown("### 🗺️ Carte des événements")
                                st.pydeck_chart(deck, use_container_width=True)

                    # --- DYNAMIQUE (pydeck) : fluide + Animation Start/Stop par time.sleep ---
                    else:
                        st.session_state.setdefault(idx_key, 0)
                        center_key = f"center_{idx_key}"
                        zoom_key   = f"zoom_{idx_key}"

                        anim_run_key   = f"anim_run_{idx_key}"       # bool
                        anim_delay_key = f"anim_delay_{idx_key}"     # int (ms)
                        anim_skip_key  = f"anim_skip_once_{idx_key}" # bool (ne pas avancer ce run)

                        st.session_state.setdefault(anim_run_key, False)
                        st.session_state.setdefault(anim_delay_key, 1000)
                        st.session_state.setdefault(anim_skip_key, False)

                        # Si pas de vue capturée : centre/zoom une fois
                        if center_key not in st.session_state or zoom_key not in st.session_state:
                            coords = []
                            for ev in events or []:
                                lieu = (ev.get("lieu") or "").strip()
                                if not lieu:
                                    continue
                                g = geocoder_lieu(lieu)
                                if g:
                                    lat, lon, _ = g
                                    coords.append((lat, lon))
                            if coords:
                                lat_c = sum(lat for lat, _ in coords) / len(coords)
                                lon_c = sum(lon for _, lon in coords) / len(coords)
                                st.session_state[center_key] = (lat_c, lon_c)
                                st.session_state[zoom_key] = 12
                            else:
                                st.session_state[center_key] = (48.8566, 2.3522)
                                st.session_state[zoom_key] = 12

                        # Contrôles ⬅️ ➡️
                        col_prev, col_pos, col_next = st.columns([1,2,1])
                        with col_prev:
                            if st.button("⬅️", help="Position précédente", key=f"prev_{idx_key}"):
                                st.session_state[idx_key] = max(0, st.session_state[idx_key] - 1)
                                st.session_state[anim_skip_key] = True
                        with col_next:
                            if st.button("➡️", help="Position suivante", key=f"next_{idx_key}"):
                                st.session_state[idx_key] = min(len(events) - 1, st.session_state[idx_key] + 1)
                                st.session_state[anim_skip_key] = True
                        with col_pos:
                            st.write(f"Position : **{st.session_state[idx_key] + 1} / {len(events)}**")

                        # Animation Start/Stop + délai
                        st.markdown("### ▶️ Animation")
                        col_start, col_delay, col_stop = st.columns([1,3,1])
                        with col_start:
                            if st.button("▶️", key=f"start_{idx_key}"):
                                st.session_state[anim_run_key] = True
                                st.session_state[anim_skip_key] = True
                                st.rerun()
                        with col_stop:
                            if st.button("⏹️", key=f"stop_{idx_key}"):
                                st.session_state[anim_run_key] = False
                                st.session_state[anim_skip_key] = True
                                st.rerun()
                        with col_delay:
                            st.slider(
                                "Délai (ms)",
                                min_value=50, max_value=3000, step=50,
                                key=anim_delay_key,
                                help="Temps entre deux positions pendant l'animation"
                            )

                        # DataFrame points (géocodé en cache)
                        person_part = selected_person if (mode_affichage != "Trajectoire globale") else ""
                        events_key = f"{selected_doc}|{mode_affichage}|{person_part}|{len(events)}"
                        df_points = build_points_df_cached(events_key, events, geocoder_lieu)

                        if df_points.empty:
                            the_map = None
                            st.info("Aucun événement géocodable trouvé.")
                        else:
                            total_pts = len(df_points)
                            if total_pts == 0:
                                the_map = None
                            else:
                                if st.session_state[idx_key] >= total_pts:
                                    st.session_state[idx_key] = 0

                                deck = _build_pydeck_dynamic_from_df(
                                    df_points,
                                    idx_zero_based=st.session_state[idx_key],
                                    center=st.session_state[center_key],
                                    zoom=st.session_state[zoom_key],
                                    selected_style_uri=selected_style_uri,
                                )

                            with col_graph:
                                
                                st.markdown("### 🗺️ Carte des événements (dynamique)")

                                map_container = st.empty()  # ✅ conteneur persistant pour mise à jour fluide
                                if deck is not None:
                                    map_container.pydeck_chart(deck, use_container_width=True)
                                else:
                                    st.info("Impossible de construire la vue dynamique (aucun point).")

                                # ✅ Boucle d'animation fluide (sans rerun complet)
                                if st.session_state[anim_run_key] and total_pts > 1:
                                    delay = int(st.session_state[anim_delay_key]) / 1000.0
                                    for step in range(st.session_state[idx_key], total_pts):
                                        df_points["is_current"] = (df_points["idx"] == (step + 1))
                                        deck = _build_pydeck_dynamic_from_df(
                                            df_points,
                                            idx_zero_based=step,
                                            center=st.session_state[center_key],
                                            zoom=st.session_state[zoom_key],
                                            selected_style_uri=selected_style_uri,
                                        )
                                        map_container.pydeck_chart(deck, use_container_width=True)
                                        time.sleep(delay)
                                    st.session_state[anim_run_key] = False

        else:
            with col_graph:
                st.info("Veuillez charger des documents puis cliquer sur 🚀 **Lancer la vue**.")



# Vue extractions informations procédure
elif view_mode == "Extractions informations procédure":
    st.title("🧾 Extractions d’informations – Procédures policières")
    st.markdown(
        """
        Cette vue permet d’extraire automatiquement les informations clés des procédures
        (`.odt`, `.doc`, `.docx`, `.txt`), de visualiser le fichier JSON obtenu, de l’éditer et de le sauvegarder.
        Vous pouvez également télécharger le JSON pour le réutiliser ailleurs.
        """
    )

    uploaded_files = st.file_uploader(
        "📂 Importez une ou plusieurs procédures",
        type=["odt", "doc", "docx", "txt"],
        accept_multiple_files=True,
        key="proc_files",
    )

    if not uploaded_files:
        st.info("💡 Importez au moins un fichier de procédure pour commencer.")
    else:
        # Dossier temporaire de travail
        with tempfile.TemporaryDirectory() as tmpdir:
            for file in uploaded_files:
                st.markdown(f"---\n### 🗂️ Fichier : `{file.name}`")

                # Sauvegarde temporaire du fichier importé
                suffix = os.path.splitext(file.name)[1].lower()
                tmp_path = os.path.join(tmpdir, file.name)
                with open(tmp_path, "wb") as tmpf:
                    tmpf.write(file.read())

                # Extraction automatique
                with st.spinner("Extraction des informations en cours..."):
                    try:
                        data = extraction_procedure(tmp_path)
                        json_str = json.dumps(data, ensure_ascii=False, indent=2)
                        st.success("✅ Extraction terminée avec succès.")
                    except Exception as e:
                        st.error(f"Erreur lors de l’extraction : {e}")
                        continue

                # Éditeur JSON
                st.markdown("#### ✏️ Éditez le contenu JSON si nécessaire :")
                edited_json = st.text_area(
                    label="JSON extrait",
                    value=json_str,
                    height=500,
                    key=f"json_edit_{file.name}",
                )

                # Boutons de sauvegarde et téléchargement
                col1b, col2b = st.columns([1, 2])
                with col1b:
                    if st.button(f"💾 Sauvegarder le JSON ({file.name})", key=f"save_{file.name}"):
                        try:
                            json_data = json.loads(edited_json)
                            json_out_path = os.path.join(tmpdir, f"{os.path.splitext(file.name)[0]}.json")
                            with open(json_out_path, "w", encoding="utf8") as f:
                                json.dump(json_data, f, ensure_ascii=False, indent=2)
                            st.success(f"✅ Sauvegardé : {json_out_path}")
                        except Exception as e:
                            st.error(f"❌ Erreur lors de la sauvegarde : {e}")

                with col2b:
                    st.download_button(
                        label=f"⬇️ Télécharger `{file.name}.json`",
                        data=edited_json.encode("utf8"),
                        file_name=f"{os.path.splitext(file.name)[0]}.json",
                        mime="application/json",
                        key=f"dl_{file.name}",
                    )

                # Vue synthétique
                st.markdown("#### 🔍 Aperçu synthétique")
                try:
                    st.json(json.loads(edited_json))
                except Exception:
                    st.warning("⚠️ Le contenu JSON est invalide – impossible d’afficher l’aperçu.")

            st.markdown("---")
            st.success("🎯 Traitement terminé pour tous les fichiers.")
