# -*- coding: utf-8 -*-
import sys
import spacy
from pyvis.network import Network

def construire_graphe_narratif(texte):
    """
    Construit un graphe narratif enrichi à partir du texte.
    - Les entités PERSON, ORG, GPE sont des nœuds
    - Les relations sujet–verbe–objet deviennent des arêtes orientées
    """
    nlp = spacy.load("fr_core_news_md")  # ou "fr_core_news_lg" si dispo
    doc = nlp(texte)

    net = Network(height="750px", width="100%", bgcolor="#0a0a0a", font_color="white", directed=True)
    net.force_atlas_2based()

    # Couleurs des types d'entités
    color_map = {"PER": "lightcoral", "PERSON": "lightcoral",
                 "ORG": "lightgreen", "GPE": "lightskyblue", "LOC": "deepskyblue"}

    # Ajouter les entités nommées comme nœuds
    for ent in doc.ents:
        color = color_map.get(ent.label_, "lightgray")
        net.add_node(ent.text, label=ent.text, title=ent.label_, color=color)

    # --- Extraction des relations (triplets sujet-verbe-objet) ---
    relations = []
    for sent in doc.sents:
        for token in sent:
            if token.pos_ == "VERB":  # On cherche les verbes centraux
                sujets = [w.text for w in token.lefts if w.dep_ in ("nsubj", "nsubj:pass")]
                objets = [w.text for w in token.rights if w.dep_ in ("obj", "obl", "xcomp")]
                for s in sujets:
                    for o in objets:
                        relations.append((s, token.lemma_, o))

    # --- Ajout des arêtes au graphe ---
    for s, v, o in relations:
        if s != o:
            net.add_node(s, color="lightcoral")
            net.add_node(o, color="lightskyblue")
            net.add_edge(s, o, label=v, color="orange", title=v)

    return net


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python graphe_narratif_relations.py chemin/vers/ton_fichier.txt")
        sys.exit(1)

    fichier = sys.argv[1]
    with open(fichier, "r", encoding="utf-8") as f:
        texte = f.read()

    print("Analyse du texte en cours...")

    net = construire_graphe_narratif(texte)
    output_file = "graphe_narratif_relations.html"
    net.write_html(output_file)
    print(f"Graphe narratif enrichi sauvegardé dans {output_file}")
