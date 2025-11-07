# -*- coding: utf-8 -*-


##############################################
# A program that displays a graph            #
#                                            #
# Last update : 2025/07/02                   #
##############################################

# graph_display.py

import os
import tempfile
from pyvis.network import Network
import matplotlib.pyplot as plt
import networkx as nx

def display_graph(G):
    """
    Affiche un graphe interactif avec PyVis.
    Ajoute le degré (nombre de liens) au-dessus des nœuds de documents (en bleu).
    """

    net = Network(
        height="600px",
        width="100%",
        directed=False,
        bgcolor="transparent",
        font_color="black",
        cdn_resources="in_line"
    )

    # --- Ajout des nœuds ---
    for node, data in G.nodes(data=True):
        group = data.get("bipartite", -1)
        color = "#3498DB" if group == 1 else "#FF5733"  # bleu = doc / rouge = concept
        size = 25 if group == 1 else 20
        degree = G.degree(node)

        # Label principal = nom du nœud
        label = node

        # Si c'est un document (groupe 1), on ajoute le degré au-dessus
        if group == 1:
            label = f"{node}\n(degré : {degree})"

        net.add_node(
            node,
            label=label,
            color=color,
            size=size,
            title=f"Document — {degree} lien(s)" if group == 1 else "Concept",
            shape="dot"
        )

    # --- Arêtes (en noir pour meilleure lisibilité) ---
    for source, target in G.edges():
        net.add_edge(source, target, color="#000000")

    # --- Sauvegarde temporaire du HTML ---
    tmp_dir = tempfile.mkdtemp()
    html_path = os.path.join(tmp_dir, "graph.html")

    html_content = net.generate_html()
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return html_path

def export_graph_image(G):
    pos = nx.spring_layout(G)
    fig, ax = plt.subplots(figsize=(10, 6))
    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color=["#FF5733" if data["bipartite"] == 0 else "#3498DB" for _, data in G.nodes(data=True)],
        node_size=800,
        font_size=10,
        edge_color="gray",
        ax=ax
    )
    return fig





