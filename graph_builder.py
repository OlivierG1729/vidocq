# -*- coding: utf-8 -*-

############################
# Graph builder            #
#                          #
# Last update : 2025/07/02 #
############################

import networkx as nx

def build_graph(concept_to_docs):
    G = nx.Graph()

    # --- Construction bipartite ---
    for concept, docs in concept_to_docs.items():
        G.add_node(concept, bipartite=0)
        for doc in docs:
            G.add_node(doc, bipartite=1)
            G.add_edge(concept, doc)

    # --- Ajout du degré au label pour les documents ---
    for node, data in G.nodes(data=True):
        deg = G.degree(node)
        if data.get("bipartite") == 1:
            data["label"] = f"{node} ({deg})"
        else:
            data["label"] = node

    return G


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

# concept_to_docs = extract_semantic_concepts(corpus, keywords, model=model, threshold=0.30)
# test = build_graph(concept_to_docs)

# test.nodes
# test.edges

# def build_graph(concept_to_docs):

#     """builds a birepartite graph, that links concepts to documents

#     Args:
#         concept_to_docs (dict): a dictionary of keys:values, with key the name of a concept and value the list of the filenames of the texts linked to this concept

#     Returns:
#         networkx.Graph: non oriented graph with the concepts (bipartite=0) and the documents (bipartite=1) as nodes
#     """

#     from pyvis.network import Network

#     net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    
#     for concept, docs in concept_to_docs.items():
#         net.add_node(concept, label=concept, color="red")  # Affiche le nom du concept
#         for doc in docs:
#             net.add_node(doc, label=doc, color="blue")  # Affiche le nom du document
#             net.add_edge(concept, doc)

#     return net




