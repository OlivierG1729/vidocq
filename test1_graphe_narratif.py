# graph_narratif.py
import sys
import spacy
from pyvis.network import Network

def construire_graphe_narratif(texte):
    """
    Construit un graphe narratif simple à partir d’un texte.
    Chaque entité nommée devient un nœud.
    """
    nlp = spacy.load("fr_core_news_md")  # ou fr_core_news_lg si tu l’as
    doc = nlp(texte)

    net = Network(height="750px", width="100%", bgcolor="#0a0a0a", font_color="white")
    net.barnes_hut()

    # --- Ajouter les entités nommées comme nœuds ---
    for ent in doc.ents:
        color = "lightblue"
        if ent.label_ in ["PER", "PERSON"]:
            color = "lightcoral"
        elif ent.label_ in ["ORG"]:
            color = "lightgreen"
        elif ent.label_ in ["LOC", "GPE"]:
            color = "lightskyblue"
        net.add_node(ent.text, label=ent.text, title=ent.label_, color=color)

    # --- Ajouter des liens simplifiés (phrases partagées) ---
    for sent in doc.sents:
        ents = [ent.text for ent in sent.ents]
        for i in range(len(ents) - 1):
            net.add_edge(ents[i], ents[i+1], color="gray")

    return net

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python graph_narratif.py chemin/vers/ton_fichier.txt")
        sys.exit(1)

    fichier = sys.argv[1]
    with open(fichier, "r", encoding="utf-8") as f:
        texte = f.read()

    print("Analyse du texte en cours...")

    net = construire_graphe_narratif(texte)

    # Sauvegarde du graphe en HTML interactif
    output_file = "graphe_narratif.html"
    net.write_html(output_file)
    print(f"Graphe narratif sauvegardé dans {output_file}")
