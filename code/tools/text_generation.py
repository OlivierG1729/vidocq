
# -*- coding: utf-8 -*-

############################
# Corpus genration         #
#                          #
# Last update : 2025/07/12 #
############################

import wikipedia
import os

# modification du répertoire de travail
nouveau_chemin = "C:/Users/olivi/OneDrive/Desktop/Travail/DATA-i/Exploration/Sujets/Extraction_semantique/Projet"
os.chdir(nouveau_chemin)
os.getcwd()

# Configuration
wikipedia.set_lang("fr")
output_dir = "wikipedia_text"
os.makedirs(output_dir, exist_ok=True)

# Liste d'articles à extraire
titres_articles = [
    "Intelligence artificielle",
    "Apprentissage automatique",
    "Intelligence artificelle générative",
    "Machine learning",
    "Deep learning",
    "Éthique",
    "Géopolitique",
    "Droit du numérique",
    "Cybersécurité",
    "Grand modèle de langage",
    "Société de l'information",
    "Technologie",
    "Politique en France",
    "Sport",
    "Judo",
    "Etats-Unis",
    "Ordinateurs",
    "Technologie"
]

# Génération des fichiers .txt
for i, titre in enumerate(titres_articles):
    try:
        contenu = wikipedia.page(titre).content
        filename = f"{i:03d}_{titre.replace(' ', '_')}.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(contenu)
        print(f"✅ {titre} sauvegardé")
    except Exception as e:
        print(f"❌ Erreur pour {titre} : {e}")

# titre = titres_articles[0]
# titre
# contenu = wikipedia.page(titre).content
# filename = f"{0:03d}_{titre.replace(' ', '_')}.txt"
# filepath = os.path.join(output_dir, filename)
# with open(filepath, "w", encoding="utf-8") as f:
#               f.write(contenu)



