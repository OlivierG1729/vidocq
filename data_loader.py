# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 12:34:26 2025

@author: olivi
"""

############################
# Documents loader         #
#                          #
# Last update : 2025/07/02 #
############################

# def load_documents(files):
#     """loads a list of files

#     Args:
#         files (list): a list of names of virtual files (UploadedFile)

#     Returns:
#         dictionary: of the form key:value with key the name of the file and value the text into this file
#     """
#     corpus = {}
#     for file in files:
#         corpus[file.name] = file.read().decode('utf-8')
#     return corpus

def load_documents(files):
    corpus = {}
    for file in files:
        # Cas Streamlit (UploadedFile)
        if hasattr(file, "read") and hasattr(file, "name"):
            corpus[file.name] = file.read().decode("utf-8")
        # Cas local (str = chemin vers le fichier)
        elif isinstance(file, str):
            with open(file, "r", encoding="utf-8") as f:
                corpus[file] = f.read()
    return corpus


file = "C:/Users/olivi/OneDrive/Desktop/Travail/DATA-i/Exploration/Sujets/Extraction_semantique/Projet/wikipedia_text/014_judo.txt"

with open("C:/Users/olivi/OneDrive/Desktop/Travail/DATA-i/Exploration/Sujets/Extraction_semantique/Projet/wikipedia_text/014_judo.txt"
, "r", encoding="utf-8") as file:
    contenu = file.read()

import os

repertoire = "C:/Users/olivi/OneDrive/Desktop/Travail/DATA-i/Exploration/Sujets/Extraction_semantique/Projet/wikipedia_text"
# files = [f for f in os.listdir(repertoire) if os.path.isfile(os.path.join(repertoire, f))]
files = [os.path.join(repertoire, f) for f in os.listdir(repertoire) if os.path.isfile(os.path.join(repertoire, f))]

files

load_documents(files)

