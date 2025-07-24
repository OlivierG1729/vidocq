
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
from graph_display import display_graph

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

from PIL import Image

# Ouvre et redimensionne l’image au format 4:1 (ex. : 1400x350)
logo_vidocq = Image.open("Logos/vidocq4.png")
logo_vidocq_resized = logo_vidocq.resize((1400, 500))  # Largeur 4x plus grande que hauteur

# Affiche dans Streamlit
st.image(logo_vidocq_resized)

# logo_vidocq = Image.open("Logos/vidocq4.PNG")  # remplace par le chemin exact de ton fichier
# st.image(logo_vidocq, width=1400)

st.markdown("---")


# --- Disposition principale ---
col1, col_graph, col2 = st.columns([4, 8, 4])

with col1:
    st.markdown("### 🔍 Méthode de recherche")
    # search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"])
    search_method = st.selectbox(
    "Méthode utilisée :",
    ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence", "Top recherche sémantique"]
)

    with st.form("param_form"):
        threshold = None
        if search_method != "Recherche exacte":
            threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
        if search_method == "Top recherche sémantique":
            n_top = st.number_input("Nombre de documents à afficher (nœuds du graphe) :", min_value=1, max_value=100, value=1, step=1)
        submitted = st.form_submit_button("Valider les paramètres")



    st.markdown("### 📄 Corpus")
    files = st.file_uploader("Chargez vos fichiers `.txt`", type="txt", accept_multiple_files=True)

with col2:
    st.markdown("### 💬 Concepts à rechercher")
    keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

with col_graph:
    st.markdown("### 🌐 Graphe des concepts")

# --- Traitement principal ---

if submitted and files and keywords_input:
    corpus = load_documents(files)
    keywords = [k.strip().lower() for k in keywords_input.split(",")]

    # Nettoyage des documents
    doc_names = list(corpus.keys())
    # doc_texts = [clean_text(corpus[doc]) for doc in doc_names]
    doc_texts = [corpus[doc] for doc in doc_names] 

  
    # 🔁 Stocke le corpus et les textes nettoyés si besoin
    st.session_state["corpus"] = corpus
    st.session_state["doc_texts"] = doc_texts  # optionnel, utile si tu veux le réutiliser

    # Traitement selon la méthode choisie
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


# if submitted and files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold)
#     elif search_method == "Top recherche sémantique":
#         concept_to_docs = extract_top_semantic_concepts(corpus, keywords, n_top)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold)

#     st.session_state["corpus"] = corpus
#     st.session_state["concept_to_docs"] = concept_to_docs
#     st.session_state["filtered"] = concept_to_docs

# --- Affichage du graphe + texte sélectionné ---
if "filtered" in st.session_state:
    G = build_graph(st.session_state["filtered"])
    html_path = display_graph(G)

    with col_graph:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=600)

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


# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# st.set_page_config(layout="wide")

# # --- Style cyber ---
# def set_cyber_style():
#     css = """
#     <style>
#     .stApp { background-color: #000c15; color: #00ffcc; font-family: 'Courier New', monospace; }
#     h1,h2,h3,h4,h5,h6 { color: #39ff14; text-shadow: 0 0 5px #39ff14; }
#     label, .stMarkdown, .stTextInput > div > div > input, .stSelectbox { color: #00ffcc !important; }
#     .stButton>button { background-color: #00ffcc; color: black; border-radius: 8px; font-weight: bold; }
#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Logos ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])
# with col1: st.image(logo_gauche, width=100)
# with col2: st.image(logo_qviz, width=400)
# with col3: st.image(logo_droit, width=100)

# st.markdown("---")

# # --- Disposition principale ---
# col1, col_graph, col2 = st.columns([4, 8, 4])

# with col1:
#     st.markdown("### 🔍 Méthode de recherche")
#     search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"])

#     with st.form("param_form"):
#         threshold = None
#         if search_method != "Recherche exacte":
#             threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
#         submitted = st.form_submit_button("Valider les paramètres")

#     st.markdown("### 📄 Corpus")
#     files = st.file_uploader("Chargez vos fichiers `.txt`", type="txt", accept_multiple_files=True)

# with col2:
#     st.markdown("### 💬 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

# # --- Affichage du graphe ---
# with col_graph:
#     st.markdown("### 🌐 Graphe des concepts")

# # --- Traitement principal ---
# if submitted and files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold)

#     st.session_state["corpus"] = corpus
#     st.session_state["concept_to_docs"] = concept_to_docs
#     st.session_state["filtered"] = concept_to_docs

# # --- Affichage du graphe + document sélectionné ---
# if "filtered" in st.session_state:
#     G = build_graph(st.session_state["filtered"])
#     html_path = display_graph(G)

#     with col_graph:
#         with open(html_path, "r", encoding="utf-8") as f:
#             html_content = f.read()
#         components.html(html_content, height=600)

#     # ✅ Sélecteur de document
#     with col2:
#         doc_choices = list(st.session_state["corpus"].keys())
#         selected_doc = st.selectbox("📁 Choisissez un document à afficher :", doc_choices)

#     # ✅ Affichage du texte dans col_graph
#     with col_graph:
#         if selected_doc:
#             st.markdown(f"### 📄 Document : **{selected_doc}**")
#             st.markdown(
#                 f"""
#                 <div style='background-color:white; color:black; padding:1em; height:200px; overflow-y:scroll; border-radius:10px;'>
#                     <pre style='white-space: pre-wrap; word-wrap: break-word;'>{st.session_state["corpus"][selected_doc]}</pre>
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.")



# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image
# import os

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_display import build_graph, display_graph
# from streamlit_js_eval import streamlit_js_eval  # 📣 JS listener

# st.set_page_config(layout="wide")

# # --- Style cyber ---
# def set_cyber_style():
#     css = """
#     <style>
#     .stApp { background-color: #000c15; color: #00ffcc; font-family: 'Courier New', monospace; }
#     h1,h2,h3,h4,h5,h6 { color: #39ff14; text-shadow: 0 0 5px #39ff14; }
#     label, .stMarkdown { color: #00ffcc !important; }
#     .stButton>button { background-color: #00ffcc; color: black; border-radius: 8px; font-weight: bold; }
#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Bandeau ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])
# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")

# # --- Colonnes principales ---
# col1, col_graph, col2 = st.columns([4, 8, 4])

# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"])

#     with st.form("param_form"):
#         threshold = None
#         if search_method != "Recherche exacte":
#             threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.5, step=0.01)
#             st.markdown(f"**Seuil saisi :** {threshold}")
#         submitted = st.form_submit_button("Valider les paramètres")

#     st.markdown("### 📝 Corpus de documents")
#     files = st.file_uploader("Chargez vos fichiers `.txt`", type="txt", accept_multiple_files=True)

# with col2:
#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

# with col_graph:
#     st.markdown("### 🌐 Graphe des concepts")

# # --- Traitement principal ---
# if submitted and files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold)

#     st.session_state["corpus"] = corpus
#     st.session_state["concept_to_docs"] = concept_to_docs

#     G = build_graph(concept_to_docs)
#     html_path = display_graph(G)

#     with col_graph:
#         with open(html_path, 'r', encoding='utf-8') as f:
#             html_content = f.read()
#         components.html(html_content, height=600)

#     # 🧠 Récupérer le noeud cliqué via JS
#     clicked_node = streamlit_js_eval(js_expressions="parent.window.clickedNode", key="clicked_node", want_output=True)

#     if clicked_node and clicked_node in corpus:
#         with col_graph:
#             st.markdown(f"### 📄 Document : **{clicked_node}**")
#             st.markdown(
#                 f"""
#                 <div style='background-color:white; color:black; padding:1em; height:200px; overflow-y:scroll; border-radius:10px;'>
#                     <pre style='white-space: pre-wrap; word-wrap: break-word;'>{corpus[clicked_node]}</pre>
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )







# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image
# import tempfile
# import os

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# st.set_page_config(layout="wide")

# # --- Style cyber ---
# def set_cyber_style():
#     st.markdown("""
#     <style>
#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }
#     h1, h2, h3 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }
#     </style>
#     """, unsafe_allow_html=True)

# set_cyber_style()

# # --- Logos ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])
# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")

# # --- Interface utilisateur ---
# col1, col_graph, col2 = st.columns([4, 8, 4])

# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox("Méthode utilisée :", ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"])

#     threshold = None
#     if search_method in ["Recherche sémantique", "Recherche par fréquence"]:
#         threshold = st.slider(
#             "Seuil de similarité",
#             0.0, 1.0,
#             0.3 if search_method == "Recherche par fréquence" else 0.6,
#             step=0.01
#         )

#     st.markdown("### 📝 Corpus de documents")
#     files = st.file_uploader("Chargez vos fichiers `.txt`", type="txt", accept_multiple_files=True)

#     submitted = st.button("Valider les paramètres")

# with col2:
#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

# with col_graph:
#     st.markdown("### 🌐 Graphe des concepts")

# # --- Traitement principal ---
# if submitted and files and keywords_input:
#     corpus = load_documents(files)
#     st.session_state["corpus"] = corpus

#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         selected = st.multiselect("Concepts affichés :", list(concept_to_docs), default=list(concept_to_docs))
#         filtered = {k: concept_to_docs[k] for k in selected}
#         st.session_state["filtered"] = filtered

#         G = build_graph(filtered)
#         st.session_state["graph"] = G

#         html_path = display_graph(G)
#         st.session_state["html_path"] = html_path
#     else:
#         st.warning("Aucun concept détecté.")

# # --- Affichage graphe (si disponible) ---
# if "html_path" in st.session_state:
#     html_path = st.session_state["html_path"]

#     with open(html_path, 'r', encoding='utf-8') as f:
#         html_content = f.read()
#     with col_graph:
#         components.html(html_content, height=600, scrolling=False)

#     # Liste des nœuds document
#     all_doc_nodes = [
#         node for node in st.session_state["graph"].nodes()
#         if st.session_state["graph"].nodes[node].get("bipartite") == 1
#     ]

#     if all_doc_nodes:
#         clicked_node = st.selectbox("🖱️ Sélectionnez un document :", all_doc_nodes)
#         doc_text = st.session_state["corpus"].get(clicked_node)

#         if doc_text:
#             with col_graph:
#                 st.markdown("### 📰 Contenu du document sélectionné")
#                 st.markdown(
#                     f"""
#                     <div style="background-color: white; color: black;
#                                 padding: 1em; border-radius: 10px;
#                                 max-height: 300px; overflow-y: scroll;
#                                 font-family: Courier New, monospace;">
#                         <pre>{doc_text}</pre>
#                     </div>
#                     """,
#                     unsafe_allow_html=True
#                 )




# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph
# import streamlit.components.v1 as components


# import base64
# from io import BytesIO

# st.set_page_config(layout="wide")

# # --- Style cyber (fond + texte) ---
# def set_cyber_style():
#     css = """
#     <style>
#     body, .stApp {
#         margin-top: 0 !important;
#         margin-bottom: 0 !important;
#         padding-top: 0 !important;
#         padding-bottom: 0 !important;
#     }

#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }

#     h1, h2, h3, h4, h5, h6 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }

#     .css-1cpxqw2, .stMarkdown, .stTextInput > div > div > input, .stSelectbox, label {
#         color: #00ffcc !important;
#     }

#     .stButton>button {
#         background-color: #00ffcc;
#         color: black;
#         border-radius: 8px;
#         font-weight: bold;
#     }

#     .stSlider > div[data-baseweb="slider"] {
#         background-color: #00ffcc33;
#     }
#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Bandeau avec logos ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])
# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")

# # --- Disposition principale ---
# col1, col_graph, col2 = st.columns([4, 8, 4])

# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox(
#         "Méthode utilisée :",
#         ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"]
#     )

#     # st.markdown("### 📝 Concepts à rechercher")
#     # keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

#     # --- Formulaire paramètres ---
#     with st.form("param_form"):
#         if search_method in ["Recherche sémantique", "Recherche par fréquence"]:
#             threshold = st.slider(
#                 "Seuil de similarité",
#                 0.0, 1.0,
#                 0.3 if search_method == "Recherche par fréquence" else 0.6,
#                 step=0.01,
#                 key="similarity_slider"
#             )
#             st.markdown(f"<p style='color:white;'>Seuil saisi : {threshold}</p>", unsafe_allow_html=True)
#         else:
#             threshold = None

#         submitted = st.form_submit_button("Valider les paramètres")

#     with col1:
#         st.markdown("### 📝 Corpus de documents")
#         files = st.file_uploader(
#             "Chargez vos fichiers `.txt`",
#             type="txt",
#             accept_multiple_files=True
#         )

# st.markdown("---")

# with col2:
#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

# with col_graph:
#     st.markdown("### 🌐 Graphe des concepts")

# # --- Traitement ---
# if submitted and files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         st.markdown("### 🔍 Filtrage des concepts")
#         selected = st.multiselect(
#             "Concepts affichés :",
#             list(concept_to_docs),
#             default=list(concept_to_docs)
#         )
#         filtered = {k: concept_to_docs[k] for k in selected}
#         st.session_state["filtered"] = filtered

#         # with col_graph:
#         #     st.markdown("### Valeur de `filtered` (concept_to_docs filtré)")
#         #     st.write(filtered)

#         G = build_graph(filtered)

#         # with col_graph:
#         #     st.write(G.nodes())

#         html_path = display_graph(G)

#         with col_graph:
#             # st.markdown("### 🌐 Graphe des concepts")
#             with open(html_path, 'r', encoding='utf-8') as f:
#                 html_content = f.read()
#             components.html(html_content, height=600, scrolling=False)
#     else:
#         with col_graph:
#             st.warning("Aucun document ne correspond aux concepts donnés.")
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.")


# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# import base64
# from io import BytesIO

# st.set_page_config(layout="wide")  # Élargit la page à 100%

# # --- Style cyber (fond + texte) ---
# def set_cyber_style():
#     css = """
#     <style>
#     body, .stApp {
#         margin-top: 0 !important;
#         margin-bottom: 0 !important;
#         padding-top: 0 !important;
#         padding-bottom: 0 !important;
#     }

#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }

#     h1, h2, h3, h4, h5, h6 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }

#     .css-1cpxqw2, .stMarkdown, .stTextInput > div > div > input, .stSelectbox, label {
#         color: #00ffcc !important;
#     }

#     .stButton>button {
#         background-color: #00ffcc;
#         color: black;
#         border-radius: 8px;
#         font-weight: bold;
#     }

#     .stSlider > div[data-baseweb="slider"] {
#         background-color: #00ffcc33;
#     }
#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Bandeau avec logos gauche + QViz + logos droite (sur une ligne) ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])

# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")  # Séparateur visuel

# # --- Disposition des colonnes principales ---
# col1, col_graph, col2 = st.columns([4, 8, 4])

# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox(
#         "Méthode utilisée :",
#         ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"]
#     )

#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

#     with st.form("param_form"):
#         if search_method in ["Recherche sémantique", "Recherche par fréquence"]:
#             threshold = st.slider(
#                 "Seuil de similarité",
#                 0.0, 1.0,
#                 0.3 if search_method == "Recherche par fréquence" else 0.6,
#                 step=0.01,
#                 key="similarity_slider"
#             )
#             st.markdown(f"<p style='color:white;'>Seuil saisi : {threshold}</p>", unsafe_allow_html=True)
#         else:
#             threshold = None

#         submitted = st.form_submit_button("Valider les paramètres")

#     if submitted and "concept_to_docs" in st.session_state and st.session_state["concept_to_docs"]:
#         st.markdown("### 🔍 Filtrage des concepts")
#         selected = st.multiselect(
#             "Concepts affichés :",
#             list(st.session_state["concept_to_docs"]),
#             default=list(st.session_state["concept_to_docs"])
#         )
#         st.session_state["filtered"] = {
#             k: st.session_state["concept_to_docs"][k] for k in selected
#         }

# st.markdown("---")  # Séparateur visuel

# with col2:
#     st.markdown("### 📄 Chargement des documents")
#     files = st.file_uploader(
#         "Chargez vos fichiers `.txt`",
#         type="txt",
#         accept_multiple_files=True
#     )

# st.markdown("---")  # Séparateur visuel

# if files and keywords_input and submitted:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         filtered = st.session_state.get("filtered", concept_to_docs)

#         with col_graph:
#             st.markdown("### Valeur de filtered (concept_to_docs filtré)")
#             st.write(filtered)

#         G = build_graph(filtered)

#         with col_graph:
#             st.write(G.nodes())

#         html_path = display_graph(G)

#         with col_graph:
#             st.markdown("### 🌐 Graphe des concepts")
#             with open(html_path, 'r', encoding='utf-8') as f:
#                 html_content = f.read()
#             components.html(html_content, height=600, scrolling=False)
#     else:
#         with col_graph:
#             st.warning("Aucun document ne correspond aux concepts donnés.")
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents, entrer des concepts et valider les paramètres pour afficher le graphe.")


# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image
# from sentence_transformers import SentenceTransformer

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# # --- Mise en page large
# st.set_page_config(layout="wide")

# # --- Style cyber
# def set_cyber_style():
#     css = """
#     <style>
#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }
#     h1, h2, h3, h4, h5, h6 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }
#     .stMarkdown, .stTextInput > div > div > input, .stSelectbox, label {
#         color: #00ffcc !important;
#     }
#     .stButton>button {
#         background-color: #00ffcc;
#         color: black;
#         border-radius: 8px;
#         font-weight: bold;
#     }
#     .stSlider > div[data-baseweb="slider"] {
#         background-color: #00ffcc33;
#     }
#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Logos bandeau
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])
# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")

# # --- Colonnes principales
# col1, col_graph, col2 = st.columns([4, 8, 4])

# # --- Cache modèle sémantique (fixe et unique)
# @st.cache_resource(show_spinner="Chargement du modèle sémantique...")
# def get_semantic_model():
#     import random
#     random.seed(42)
#     return SentenceTransformer("all-MiniLM-L6-v2")

# # --- Colonne gauche
# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox(
#         "Méthode utilisée :",
#         ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"]
#     )

#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

#     threshold = st.slider("Seuil de similarité", 0.00, 1.00, 0.60, step = 0.01, key="similarity_slider")
#     st.markdown(f"<p style='color:white;'>Seuil saisi : {threshold}</p>", unsafe_allow_html=True)


#     # if search_method in ["Recherche sémantique", "Recherche par fréquence"]:
#     #     threshold = st.slider(
#     #         "Seuil de similarité",
#     #         0.0, 1.0,
#     #         0.6 if search_method == "Recherche sémantique" else 0.3,
#     #         step=0.01,
#     #         key="similarity_slider"
#     #     )
#     #     st.markdown(f"<p style='color:white;'>Seuil saisi : {threshold}</p>", unsafe_allow_html=True)
#     # else:
#     #     threshold = None

#     if "concept_to_docs" in st.session_state and st.session_state["concept_to_docs"]:
#         st.markdown("### 🔍 Filtrage des concepts")
#         selected = st.multiselect(
#             "Concepts affichés :",
#             list(st.session_state["concept_to_docs"]),
#             default=list(st.session_state["concept_to_docs"])
#         )
#         st.session_state["filtered"] = {
#             k: st.session_state["concept_to_docs"][k] for k in selected
#         }

# st.markdown("---")

# # --- Colonne droite
# with col2:
#     st.markdown("### 📄 Chargement des documents")
#     files = st.file_uploader(
#         "Chargez vos fichiers `.txt`",
#         type="txt",
#         accept_multiple_files=True
#     )

# st.markdown("---")

# # --- Traitement principal
# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         model = get_semantic_model()
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, model=model, threshold=threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         filtered = st.session_state.get("filtered", concept_to_docs)

#         with col_graph:
#             st.markdown("### 📋 Concepts extraits (filtrés)")
#             st.write(filtered)

#         G = build_graph(filtered)

#         with col_graph:
#             st.markdown("### 🧩 Nœuds du graphe")
#             st.write(list(G.nodes()))

#         html_path = display_graph(G)

#         with col_graph:
#             st.markdown("### 🌐 Graphe des concepts")
#             with open(html_path, 'r', encoding='utf-8') as f:
#                 html_content = f.read()
#             components.html(html_content, height=600, scrolling=False)
#     else:
#         with col_graph:
#             st.warning("Aucun concept trouvé.")
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents et entrer des concepts pour afficher le graphe.")







# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts, extract_semantic_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# import base64
# from io import BytesIO

# st.set_page_config(layout="wide")  # Élargit la page à 100%

# # --- Style cyber (fond + texte) ---
# def set_cyber_style():
#     css = """
#     <style>

#     body, .stApp {
#     margin-top: 0 !important;
#     margin-bottom: 0 !important;
#     padding-top: 0 !important;
#     padding-bottom: 0 !important;
# }

#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }

#     h1, h2, h3, h4, h5, h6 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }

#     .css-1cpxqw2, .stMarkdown, .stTextInput > div > div > input, .stSelectbox, label {
#         color: #00ffcc !important;
#     }

#     .stButton>button {
#         background-color: #00ffcc;
#         color: black;
#         border-radius: 8px;
#         font-weight: bold;
#     }

#     .stSlider > div[data-baseweb="slider"] {
#         background-color: #00ffcc33;
#     }

#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# # --- Bandeau avec logos gauche + QViz + logos droite (sur une ligne) ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_qviz = Image.open("logos/QViz.png")
# logo_droit = Image.open("logos/logo2.PNG")

# col1, col2, col3 = st.columns([1, 2, 1])

# with col1:
#     st.image(logo_gauche, width=100)
# with col2:
#     st.image(logo_qviz, width=400)
# with col3:
#     st.image(logo_droit, width=100)

# st.markdown("---")  # Séparateur visuel

# # --- Disposition des colonnes principales ---
# col1, col_graph, col2 = st.columns([4, 8, 4])  # Largeur renforcée

# # --- Colonne gauche : Méthode & concepts ---
# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox(
#         "Méthode utilisée :",
#         ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"]
#     )

#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

    
#     if search_method in ["Recherche sémantique", "Recherche par fréquence"]:
#         threshold = st.slider(
#             "Seuil de similarité",
#             0.0, 1.0,
#             0.3 if search_method == "Recherche par fréquence" else 0.6,
#             step=0.0001)
#         st.markdown(f"<p style='color:white;'>Seuil saisi par l'utilisateur : {threshold}</p>", unsafe_allow_html=True)
#     else:
#         threshold = None

#     if "concept_to_docs" in st.session_state and st.session_state["concept_to_docs"]:
#         st.markdown("### 🔍 Filtrage des concepts")
#         selected = st.multiselect(
#             "Concepts affichés :",
#             list(st.session_state["concept_to_docs"]),
#             default=list(st.session_state["concept_to_docs"])
#         )
#         st.session_state["filtered"] = {
#             k: st.session_state["concept_to_docs"][k] for k in selected
#         }

# st.markdown("---")  # Séparateur visuel

# # --- Colonne droite : Chargement des documents ---
# with col2:
#     st.markdown("### 📄 Chargement des documents")
#     files = st.file_uploader(
#         "Chargez vos fichiers `.txt`",
#         type="txt",
#         accept_multiple_files=True
#     )

# st.markdown("---")  # Séparateur visuel

# # --- Traitement et affichage du graphe ---
# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     key = f"{search_method}-{','.join(keywords)}-{threshold}"

#     if "cache" not in st.session_state:
#         st.session_state["cache"] = {}

#     if key in st.session_state["cache"]:
#         concept_to_docs = st.session_state["cache"][key]
#     else:
#         if search_method == "Recherche exacte":
#             concept_to_docs = extract_exact_concepts(corpus, keywords)
#         elif search_method == "Recherche sémantique":
#             concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#         else:
#             concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#         st.session_state["cache"][key] = concept_to_docs


#     # if search_method == "Recherche exacte":
#     #     concept_to_docs = extract_exact_concepts(corpus, keywords)
#     # elif search_method == "Recherche sémantique":
#     #     concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     # else:
#     #     concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         filtered = st.session_state.get("filtered", concept_to_docs)

#         with col_graph:
#             st.markdown("### Valeur de filtered (concept_to_docs filtré)")
#             st.write(filtered)  # Affiche le dictionnaire complet de façon lisible

#         G = build_graph(filtered)

#         with col_graph:
#             st.write(G.nodes())



#         html_path = display_graph(G)

#         with col_graph:
#             st.markdown("### 🌐 Graphe des concepts")
#             with open(html_path, 'r', encoding='utf-8') as f:
#                 html_content = f.read()
#             components.html(html_content, height=600, scrolling=False)
#     else:
#         with col_graph:
#             st.warning("Aucun document ne correspond aux concepts donnés.")
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents et entrer des concepts pour afficher le graphe.")







# ############################
# # Application              #
# #                          #
# # Last update : 2025/07/08 #
# ############################


# import streamlit as st
# import streamlit.components.v1 as components
# from PIL import Image

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# import base64
# from io import BytesIO


# st.set_page_config(layout="wide")  # Élargit la page à 100%

# # --- Style cyber (fond + texte) ---
# def set_cyber_style():
#     css = """
#     <style>
#     .stApp {
#         background-color: #000c15;
#         color: #00ffcc;
#         font-family: 'Courier New', monospace;
#     }

#     h1, h2, h3, h4, h5, h6 {
#         color: #39ff14;
#         text-shadow: 0 0 5px #39ff14;
#     }

#     .css-1cpxqw2, .stMarkdown, .stTextInput > div > div > input, .stSelectbox, label {
#         color: #00ffcc !important;
#     }

#     .stButton>button {
#         background-color: #00ffcc;
#         color: black;
#         border-radius: 8px;
#         font-weight: bold;
#     }

#     .stSlider > div[data-baseweb="slider"] {
#         background-color: #00ffcc33;
#     }

#     </style>
#     """
#     st.markdown(css, unsafe_allow_html=True)

# set_cyber_style()

# def get_base64_of_bin_file(bin_file_path):
#     with open(bin_file_path, 'rb') as f:
#         data = f.read()
#     return base64.b64encode(data).decode()

# def set_header_background(image_path, height="300px"):
#     bin_str = get_base64_of_bin_file(image_path)
#     css = f"""
#     <style>
#     .header-container {{
#         background-image: url("data:image/png;base64,{bin_str}");
#         background-repeat: no-repeat;
#         background-position: center top;
#         background-size: contain;
#         height: {height};
#         margin-bottom: 2rem;
#     }}
#     </style>
#     <div class="header-container"></div>
#     """
#     st.markdown(css, unsafe_allow_html=True)


# set_header_background("logos/QViz.png")



# # affiche un logo QViz
# # st.markdown("""
# #     <h1 style='text-align: center; font-size: 3.5em; font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; color: #4E9F3D; margin-top: 0em;'>
# #         QViz
# #     </h1>
# # """, unsafe_allow_html=True)


# # --- Logos en haut ---
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_droit = Image.open("logos/logo2.PNG")

# logo_col1, spacer, logo_col2 = st.columns([4, 0.2, 4])
# with logo_col1:
#     st.image(logo_gauche, width=140)
# # with logo_col2:
# #     st.image(logo_droit, width=140)

# st.markdown("---")  # Séparateur visuel

# # --- Disposition des colonnes principales ---
# col1, col_graph, col2 = st.columns([4, 8, 4])  # Largeur renforcée




# # --- Colonne gauche : Méthode & concepts ---
# with col1:
#     st.markdown("### 🧠 Méthode de recherche")
#     search_method = st.selectbox(
#         "Méthode utilisée :",
#         ["Recherche exacte", "Recherche sémantique", "Recherche par fréquence"]
#     )

#     st.markdown("### 📝 Concepts à rechercher")
#     keywords_input = st.text_input("Entrez les concepts (séparés par des virgules)")

#     if search_method in ["Recherche sémantique", "TF-IDF + cosine similarity"]:
#         threshold = st.slider(
#             "Seuil de similarité",
#             0.0, 1.0,
#             0.3 if search_method == "Recherche par fréquence" else 0.6,
#             step=0.05
#         )
#     else:
#         threshold = None

#     if "concept_to_docs" in st.session_state and st.session_state["concept_to_docs"]:
#         st.markdown("### 🔍 Filtrage des concepts")
#         selected = st.multiselect(
#             "Concepts affichés :",
#             list(st.session_state["concept_to_docs"]),
#             default=list(st.session_state["concept_to_docs"])
#         )
#         st.session_state["filtered"] = {
#             k: st.session_state["concept_to_docs"][k] for k in selected
#         }

# st.markdown("---")  # Séparateur visuel

# # --- Colonne droite : Chargement des documents ---
# with col2:
#     st.image(logo_droit, width=140)
#     st.markdown("### 📄 Chargement des documents")
#     files = st.file_uploader(
#         "Chargez vos fichiers `.txt`",
#         type="txt",
#         accept_multiple_files=True
#     )



# st.markdown("---")  # Séparateur visuel

# # --- Traitement et affichage du graphe ---
# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         from concept_extractor import extract_semantic_concepts
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     st.session_state["concept_to_docs"] = concept_to_docs

#     if concept_to_docs:
#         filtered = st.session_state.get("filtered", concept_to_docs)
#         G = build_graph(filtered)
#         html_path = display_graph(G)

#         with col_graph:
#             st.markdown("### 🌐 Graphe des concepts")
#             with open(html_path, 'r', encoding='utf-8') as f:
#                 html_content = f.read()
#             components.html(html_content, height=600, scrolling=False)
#     else:
#         with col_graph:
#             st.warning("Aucun document ne correspond aux concepts donnés.")
# else:
#     with col_graph:
#         st.info("Veuillez charger des documents et entrer des concepts pour afficher le graphe.")














# import streamlit as st
# import streamlit.components.v1 as components

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# from PIL import Image


# st.title("Explorateur de concepts")

# # Chargement des logos
# logo_gauche = Image.open("logos/logo1.PNG")
# logo_droit = Image.open("logos/logo2.PNG")

# # Affichage des logos dans deux colonnes
# col1, col2 = st.columns([1, 1])  # Équilibré

# with col1:
#     st.image(logo_gauche, width=150)

# with col2:
#     st.image(logo_droit, width=150)


# # Sidebar : tout dedans
# with st.sidebar:
#     search_method = st.selectbox(
#         "Méthode de recherche",
#         ["Recherche exacte", "Recherche sémantique", "TF-IDF + cosine similarity"]
#     )

#     files = st.file_uploader("Chargez vos fichiers .txt", type="txt", accept_multiple_files=True)

#     keywords_input = st.text_input("Entrez les concepts, séparés par des virgules")

#     # Affichage conditionnel du slider selon la méthode
#     if search_method in ["Recherche sémantique", "TF-IDF + cosine similarity"]:
#         threshold = st.slider("Seuil de similarité", 0.0, 1.0, 0.3 if search_method=="TF-IDF + cosine similarity" else 0.6, step=0.05)
#     else:
#         threshold = None

# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         from concept_extractor import extract_semantic_concepts
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:  # TF-IDF + cosine similarity
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     # Filtrage des concepts à afficher
#     if concept_to_docs:
#         selected = st.sidebar.multiselect("Filtrer les concepts :", list(concept_to_docs), default=list(concept_to_docs))
#         filtered = {k: concept_to_docs[k] for k in selected}

#         G = build_graph(filtered)
#         html_path = display_graph(G)

#         with open(html_path, 'r', encoding='utf-8') as f:
#             html_content = f.read()
#         components.html(html_content, height=600, scrolling=True)
#     else:
#         st.warning("Aucun document ne correspond aux concepts donnés.")


# import streamlit as st
# import streamlit.components.v1 as components

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts, extract_tfidf_concepts  # Assure-toi de bien importer la nouvelle fonction
# from graph_builder import build_graph
# from graph_display import display_graph

# st.title("Explorateur de concepts")

# search_method = st.sidebar.selectbox(
#     "Méthode de recherche",
#     ["Recherche exacte", "Recherche sémantique", "TF-IDF + cosine similarity"]
# )

# files = st.file_uploader("Chargez vos fichiers .txt", type="txt", accept_multiple_files=True)
# keywords_input = st.text_input("Entrez les concepts, séparés par des virgules")

# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     elif search_method == "Recherche sémantique":
#         from concept_extractor import extract_semantic_concepts
#         threshold = st.sidebar.slider("Seuil de similarité", 0.0, 1.0, 0.6, step=0.05)
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)
#     else:  # TF-IDF + cosine similarity
#         threshold = st.sidebar.slider("Seuil de similarité", 0.0, 1.0, 0.3, step=0.05)
#         concept_to_docs = extract_tfidf_concepts(corpus, keywords, threshold=threshold)

#     if concept_to_docs:
#         selected = st.multiselect("Filtrer les concepts :", list(concept_to_docs), default=list(concept_to_docs))
#         filtered = {k: concept_to_docs[k] for k in selected}

#         G = build_graph(filtered)
#         html_path = display_graph(G)

#         with open(html_path, 'r', encoding='utf-8') as f:
#             html_content = f.read()
#         components.html(html_content, height=600, scrolling=True)
#     else:
#         st.warning("Aucun document ne correspond aux concepts donnés.")




# import streamlit as st
# import streamlit.components.v1 as components

# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# st.title("Explorateur de concepts")

# # Choix de la méthode de recherche dans la sidebar
# search_method = st.sidebar.selectbox(
#     "Méthode de recherche",
#     ["Recherche exacte", "Recherche sémantique"]
# )

# # Upload et saisie des mots-clés
# files = st.file_uploader("Chargez vos fichiers .txt", type="txt", accept_multiple_files=True)
# keywords_input = st.text_input("Entrez les concepts, séparés par des virgules")

# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]

#     # Appel de la fonction selon la méthode choisie
#     if search_method == "Recherche exacte":
#         concept_to_docs = extract_exact_concepts(corpus, keywords)
#     else:
#         from concept_extractor import extract_semantic_concepts
#         threshold = st.sidebar.slider("Seuil de similarité", 0.0, 1.0, 0.6, step=0.05)
#         concept_to_docs = extract_semantic_concepts(corpus, keywords, threshold=threshold)

#     if concept_to_docs:
#         selected = st.multiselect("Filtrer les concepts :", list(concept_to_docs), default=list(concept_to_docs))
#         filtered = {k: concept_to_docs[k] for k in selected}

#         G = build_graph(filtered)
#         html_path = display_graph(G)

#         with open(html_path, 'r', encoding='utf-8') as f:
#             html_content = f.read()
#         components.html(html_content, height=600, scrolling=True)
#     else:
#         st.warning("Aucun document ne correspond aux concepts donnés.")


# import streamlit as st

# import streamlit.components.v1 as components
# from data_loader import load_documents
# from concept_extractor import extract_exact_concepts
# from graph_builder import build_graph
# from graph_display import display_graph

# st.title("Explorateur de concepts")

# files = st.file_uploader("Chargez vos fichiers .txt", type="txt", accept_multiple_files=True)
# keywords_input = st.text_input("Entrez les concepts, séparés par des virgules")

# if files and keywords_input:
#     corpus = load_documents(files)
#     keywords = [k.strip().lower() for k in keywords_input.split(",")]
#     concept_to_docs = extract_exact_concepts(corpus, keywords)

#     selected = st.multiselect("Filtrer les concepts :", list(concept_to_docs), default=list(concept_to_docs))
#     filtered = {k: concept_to_docs[k] for k in selected}

#     G = build_graph(filtered)
#     html_path = display_graph(G)

#     # with open(html_path, "r", encoding="utf-8") as f:
#     #     graph_html = f.read()
#     # st.components.v1.html(graph_html, height=600)

#     with open(html_path, 'r', encoding='utf-8') as f:
#         html_content = f.read()
    
#     components.html(html_content, height=600, scrolling=True)
