# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 12:34:26 2025

@author: olivi
"""

############################
# Concept extractor        #
#                          #
# Last update : 2025/07/02 #
############################


from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer, util
import numpy as np
import re
import unicodedata
import spacy
from spacy.lang.fr.stop_words import STOP_WORDS

# 🧠 Chargement du modèle sémantique
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')

# Charge le modèle français de spaCy
nlp = spacy.load("fr_core_news_md")  # ou "sm" si tu veux une version plus légère

def clean_text(text):
    if not isinstance(text, str):
        text = str(text)

    # 🔡 Met en minuscules
    text = text.lower()

    # 🧼 Supprime les accents
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode("utf-8")

    # 🧹 Supprime la ponctuation
    text = re.sub(r'[^\w\s-]', ' ', text)

    # 🧵 Supprime les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()

    # 🧬 Lemmatisation + suppression des stopwords
    doc = nlp(text)
    lemmatized = [token.lemma_ for token in doc if token.lemma_ not in STOP_WORDS and not token.is_punct]

    # 🚀 Retourne le texte nettoyé
    return " ".join(lemmatized)

def clean_text_light(text):
    if not isinstance(text, str):
        text = str(text)

    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode("utf-8")
    text = re.sub(r'[^\w\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_exact_concepts(corpus, keywords):
    # 🔡 Nettoie les mots-clés (minuscules, suppression accents, etc.)
    cleaned_keywords = [clean_text_light(k) for k in keywords]
    concept_to_docs = {keyword: [] for keyword in keywords}

    for doc_name, doc_text in corpus.items():
        doc_text_clean = clean_text_light(doc_text)

        for original_keyword, cleaned_keyword in zip(keywords, cleaned_keywords):
            if cleaned_keyword in doc_text_clean:
                concept_to_docs[original_keyword].append(doc_name)

    return {k: v for k, v in concept_to_docs.items() if v}


# def extract_exact_concepts(corpus, keywords):
#     concept_to_docs = {keyword: [] for keyword in keywords}

#     for doc_name, doc_text in corpus.items():
#         doc_text_clean = clean_text(doc_text)
#         for keyword in keywords:
#             if keyword in doc_text_clean:
#                 concept_to_docs[keyword].append(doc_name)
    
#     return {k: v for k, v in concept_to_docs.items() if v}


def extract_tfidf_concepts(corpus, keywords, threshold=0.3):
    doc_names = list(corpus.keys())
    doc_texts = [clean_text_light(corpus[doc]) for doc in doc_names]

    # vectorizer = TfidfVectorizer()
    vectorizer = TfidfVectorizer(ngram_range=(1, 3))  # Unigrammes, bigrammes, trigrammes
    tfidf_matrix = vectorizer.fit_transform(doc_texts)
    feature_names = vectorizer.get_feature_names_out()

    keyword_vectors = []
    for keyword in keywords:
        if keyword in feature_names:
            idx = np.where(feature_names == keyword)[0][0]
            keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
            keyword_vectors.append((keyword, keyword_vector))
        else:
            # 🔍 Tentative de récupération de variantes partielles
            matches = [f for f in feature_names if keyword in f]
            for match in matches:
                idx = np.where(feature_names == match)[0][0]
                keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
                keyword_vectors.append((match, keyword_vector))

    # for keyword in keywords:
    #     if keyword in feature_names:
    #         idx = np.where(feature_names == keyword)[0][0]
    #         keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
    #         keyword_vectors.append((keyword, keyword_vector))

    concept_to_docs = {keyword: [] for keyword in keywords}
    for keyword, vector in keyword_vectors:
        for i, score in enumerate(vector):
            if score >= threshold:
                concept_to_docs[keyword].append(doc_names[i])

    return {k: v for k, v in concept_to_docs.items() if v}


def extract_semantic_concepts(corpus, keywords, threshold=0.5):
    doc_names = list(corpus.keys())
    doc_texts = [clean_text_light(corpus[doc]) for doc in doc_names]

    # 🔐 Sécurise l'encodage des documents
    doc_embeddings = model.encode(doc_texts, convert_to_tensor=True)
    # doc_embeddings = st.session_state["doc_embeddings"]
    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)

    concept_to_docs = {keyword: [] for keyword in keywords}

    for i, keyword in enumerate(keywords):
        keyword_emb = keyword_embeddings[i]
        similarities = util.pytorch_cos_sim(keyword_emb, doc_embeddings)[0]

        for j, score in enumerate(similarities):
            if score >= threshold:
                concept_to_docs[keyword].append(doc_names[j])

    return {k: v for k, v in concept_to_docs.items() if v}


def extract_top_semantic_concepts(corpus, keywords, top_n=10):
    doc_names = list(corpus.keys())
    doc_texts = [clean_text_light(corpus[doc]) for doc in doc_names]

    # 🔐 Encodage des documents et des mots-clés
    doc_embeddings = model.encode(doc_texts, convert_to_tensor=True)    
    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)

    # 🔍 Moyenne des vecteurs des mots-clés pour une représentation globale
    mean_keyword_embedding = keyword_embeddings.mean(dim=0)

    # 💡 Calcul des similarités cosinus entre chaque document et les mots-clés
    similarities = util.pytorch_cos_sim(mean_keyword_embedding, doc_embeddings)[0]  # vecteur des scores

    # 📊 Sélection des n documents les plus proches
    top_indices = similarities.argsort(descending=True)[:top_n]
    top_docs = [doc_names[i] for i in top_indices]

    # 🔙 Format compatible avec ton graphe
    concept_to_docs = {"Top recherche sémantique": top_docs}
    return concept_to_docs



# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np
# from sentence_transformers import SentenceTransformer, util

# model = SentenceTransformer("all-MiniLM-L6-v2")

# def extract_exact_concepts(corpus, keywords):
#     """Extraction of a concept into a corpus of text documents

#     Args:
#         corpus (dictionary): a dictionary, which of key is the name of the document and the value is the text
#         keywords (_type_): a list of strings

#     Returns:
#         dictionary: the dictionary of keys:values, where key is the concept and value is the list of the documents that contain the concept
#     """

#     result = {}
#     for concept in keywords:
#         concept = concept.strip().lower()
#         result[concept] = []
#         for doc, text in corpus.items():
#             if concept in text.lower():
#                 result[concept].append(doc)
#     return result


# def extract_semantic_concepts(corpus, keywords, model=model, threshold=0.6):

#     import random
#     random.seed(42)  # 42 est un exemple, tu peux mettre n'importe quel entier

#     doc_names = sorted(corpus.keys())  # ordonner les documents de façon stable
#     doc_texts = [corpus[k] for k in doc_names]
#     doc_embeddings = model.encode(doc_texts, convert_to_tensor=True)

#     result = {}

#     for concept in keywords:
#         concept_embedding = model.encode(concept, convert_to_tensor=True)
#         similarities = util.cos_sim(concept_embedding, doc_embeddings)[0]
#         matched_docs = [doc_names[i] for i, score in enumerate(similarities) if score >= threshold]
#         result[concept] = matched_docs

#     return result

# # CHECK : on vérifie la fonction d'extraction sémantique : est-elle cohérente vis-à-vid su seuil ?
# import os
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
# import numpy as np
# from sentence_transformers import SentenceTransformer, util

# model = SentenceTransformer("all-MiniLM-L6-v2")

# directory = "C:/Users/olivi/OneDrive/Desktop/Travail/DATA-i/Exploration/Sujets/Extraction_semantique/Projet/wikipedia_text"
# corpus = {}

# for filename in os.listdir(directory):
#     complete_name = os.path.join(directory, filename)
#     with(open(complete_name, "r", encoding = "utf-8")) as f:
#         text = f.read()
#         corpus[filename] = text

# corpus["014_Judo.txt"]
# keywords = ["intelligence artificielle"]

# extract_semantic_concepts(corpus, keywords, model=model, threshold=0.1591)
# # Réponse : oui, elle est cohérente. Le problème vient donc de l'interface.



# def extract_tfidf_concepts(corpus, keywords, threshold=0.6):
#     """
#     Extraction of concepts by TF-IDF + cosine similarity.

#     Args:
#         corpus (dict): keys=doc names, values=text strings
#         keywords (list of str): concepts to search for
#         threshold (float): similarity threshold to consider a document relevant

#     Returns:
#         dict: keys=concept, values=list of doc names matching
#     """

#     result = {}
#     docs = list(corpus.values())
#     doc_names = list(corpus.keys())

#     # On vectorise le corpus en TF-IDF (uni-grammes)
#     vectorizer = TfidfVectorizer(stop_words='english')
#     tfidf_docs = vectorizer.fit_transform(docs)  # shape = (n_docs, n_terms)

#     for concept in keywords:
#         concept = concept.strip().lower()

#         # On vectorise le concept comme un mini-document
#         tfidf_concept = vectorizer.transform([concept])  # shape = (1, n_terms)

#         # Calcul de similarité cosinus entre concept et chaque doc
#         cosine_similarities = cosine_similarity(tfidf_concept, tfidf_docs).flatten()

#         # Récupérer les docs dont la similarité dépasse le seuil
#         matched_docs = [doc_names[i] for i, score in enumerate(cosine_similarities) if score >= threshold]

#         result[concept] = matched_docs

#     return result





