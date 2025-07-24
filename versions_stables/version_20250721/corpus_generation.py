
# -*- coding: utf-8 -*-

############################
# Corpus genration         #
#                          #
# Last update : 2025/07/11 #
############################

import os
import csv
import random
from faker import Faker

# Configuration
faker = Faker("fr_FR")
random.seed(42)

output_dir = "corpus_100_long"
os.makedirs(output_dir, exist_ok=True)

# Thématiques
themes = [
    "IA_math", "IA_info", "IA_droit", "IA_ethique", "IA_societe",
    "societe_variee", "actu_politique", "actu_eco", "geopolitique"
]

# Génération des fichiers
annotations = []
for i in range(100):
    # Choix aléatoire de 1 à 3 thèmes
    n_themes = random.choices([1, 2, 3], weights=[0.5, 0.3, 0.2])[0]
    theme_indices = sorted(random.sample(range(9), n_themes))
    selected_themes = [themes[j] for j in theme_indices]

    # Texte long : au moins 50 phrases réparties sur 10 paragraphes
    titre = f"Titre : {faker.sentence()}"
    theme_line = f"Thèmes : {', '.join(selected_themes)}"
    paragraphs = "\n\n".join(faker.paragraph(nb_sentences=5) for _ in range(10))
    content = f"{titre}\n\n{theme_line}\n\n{paragraphs}"

    # Sauvegarde
    filename = f"doc_{i:03d}.txt"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    # Ajout à l'annotation
    annotation_row = [1 if j in theme_indices else 0 for j in range(9)]
    annotations.append([filename] + annotation_row)

# Écriture du fichier CSV d'annotations
csv_path = os.path.join(output_dir, "annotations.csv")
with open(csv_path, "w", newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["filename"] + themes)
    writer.writerows(annotations)

print(f"✅ 100 fichiers .txt et le fichier annotations.csv ont été créés dans : {output_dir}")
