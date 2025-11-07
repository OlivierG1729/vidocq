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


from sentence_transformers import util
import numpy as np
import re
import unicodedata
import spacy
from spacy.lang.fr.stop_words import STOP_WORDS

from lib.indexing import IndexData, get_index_manager


index_manager = get_index_manager()

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


def extract_exact_concepts(index_data: IndexData, keywords):
    # 🔡 Nettoie les mots-clés (minuscules, suppression accents, etc.)
    cleaned_keywords = [clean_text_light(k) for k in keywords]
    concept_to_docs = {}

    for original_keyword, cleaned_keyword in zip(keywords, cleaned_keywords):
        docs_from_index = set(index_data.inverted_index.get(cleaned_keyword, []))

        if not docs_from_index:
            for doc_name, doc_text_clean in index_data.clean_documents.items():
                if cleaned_keyword in doc_text_clean:
                    docs_from_index.add(doc_name)

        if docs_from_index:
            concept_to_docs[original_keyword] = sorted(docs_from_index)

    return concept_to_docs


# def extract_exact_concepts(corpus, keywords):
#     concept_to_docs = {keyword: [] for keyword in keywords}

#     for doc_name, doc_text in corpus.items():
#         doc_text_clean = clean_text(doc_text)
#         for keyword in keywords:
#             if keyword in doc_text_clean:
#                 concept_to_docs[keyword].append(doc_name)
    
#     return {k: v for k, v in concept_to_docs.items() if v}


def extract_tfidf_concepts(index_data: IndexData, keywords, threshold=0.3):
    doc_names = index_data.doc_order
    tfidf_matrix = index_data.tfidf_matrix
    vectorizer = index_data.tfidf_vectorizer
    feature_names = vectorizer.get_feature_names_out()

    keyword_vectors = []
    cleaned_keywords = [clean_text_light(keyword) for keyword in keywords]
    for original_keyword, cleaned_keyword in zip(keywords, cleaned_keywords):
        if cleaned_keyword in feature_names:
            idx = np.where(feature_names == cleaned_keyword)[0][0]
            keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
            keyword_vectors.append((original_keyword, keyword_vector))
        else:
            matches = [f for f in feature_names if cleaned_keyword in f]
            for match in matches:
                idx = np.where(feature_names == match)[0][0]
                keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
                keyword_vectors.append((original_keyword, keyword_vector))

    # for keyword in keywords:
    #     if keyword in feature_names:
    #         idx = np.where(feature_names == keyword)[0][0]
    #         keyword_vector = tfidf_matrix[:, idx].toarray().flatten()
    #         keyword_vectors.append((keyword, keyword_vector))

    concept_to_docs = {}
    for keyword, vector in keyword_vectors:
        matching_docs = [doc_names[i] for i, score in enumerate(vector) if score >= threshold]
        if matching_docs:
            concept_to_docs[keyword] = matching_docs

    return concept_to_docs


from sentence_transformers import util

def extract_semantic_concepts(index_data: IndexData, keywords, threshold=0.5):
    """
    Associe chaque concept aux documents contenant au moins un passage
    dont la similarité sémantique dépasse le seuil donné.
    """
    model = index_data.model if hasattr(index_data, "model") else index_manager.model
    passage_embeddings = index_data.as_tensor()
    passage_to_doc = index_data.passage_to_doc

    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)
    concept_to_docs = {kw: set() for kw in keywords}

    for i, keyword in enumerate(keywords):
        kw_emb = keyword_embeddings[i]
        similarities = util.pytorch_cos_sim(kw_emb, passage_embeddings)[0]

        for j, score in enumerate(similarities):
            if score >= threshold:
                doc_name = passage_to_doc[j]
                concept_to_docs[keyword].add(doc_name)

    # Conversion des sets en listes triées
    return {k: sorted(v) for k, v in concept_to_docs.items() if v}




from sentence_transformers import util

def extract_top_semantic_concepts(index_data: IndexData, keywords, top_n=3):
    """
    Associe chaque concept aux documents contenant les passages les plus proches sémantiquement.
    Retourne, pour chaque concept, la liste des top_n documents les plus pertinents.
    """
    model = index_data.model if hasattr(index_data, "model") else index_manager.model
    passage_embeddings = index_data.as_tensor()
    passage_to_doc = index_data.passage_to_doc

    keyword_embeddings = model.encode(keywords, convert_to_tensor=True)
    concept_to_docs = {}

    for i, keyword in enumerate(keywords):
        kw_emb = keyword_embeddings[i]
        similarities = util.pytorch_cos_sim(kw_emb, passage_embeddings)[0]

        # Tri décroissant des passages les plus proches
        top_indices = similarities.argsort(descending=True)

        top_docs = []
        for idx in top_indices:
            doc_name = passage_to_doc[idx]
            if doc_name not in top_docs:
                top_docs.append(doc_name)
            if len(top_docs) >= top_n:
                break

        concept_to_docs[keyword] = top_docs

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





