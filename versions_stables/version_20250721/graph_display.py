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

def display_graph(G):
    # net = Network(height="600px", width="100%", directed=False, bgcolor="#111", font_color="white")
    # net = Network(height="600px", width="100%", directed=False, bgcolor="#FFDAB9", font_color="black")
    net = Network(height="600px", width="100%", directed=False, bgcolor="transparent", font_color="black")



    for node, data in G.nodes(data=True):
        group = data.get("bipartite", -1)
        color = "#3498DB" if group == 1 else "#FF5733"
        size = 25 if group == 1 else 20

        net.add_node(
            node,
            label=node,
            color=color,
            size=size,
            title="Concept" if group == 0 else "Document",
            shape="dot"
        )

    for source, target in G.edges():
        net.add_edge(source, target)

    tmp_dir = tempfile.mkdtemp()
    html_path = os.path.join(tmp_dir, "graph.html")
    net.save_graph(html_path)
    return html_path


# import os
# import tempfile
# from pyvis.network import Network

# selected_node_path = os.path.join(tempfile.gettempdir(), "selected_node.txt")

# def display_graph(G):
#     """Create an interactive graph visualization with clickable nodes."""
#     net = Network(height="600px", width="100%", notebook=False, bgcolor="#000c15", font_color="#00ffcc")

#     net.set_options('''
#     var options = {
#       "nodes": {
#         "shape": "dot",
#         "size": 20,
#         "font": {
#           "size": 20,
#           "color": "#ffffff"
#         }
#       },
#       "edges": {
#         "width": 2,
#         "color": {
#           "color": "#00ffcc"
#         }
#       },
#       "physics": {
#         "barnesHut": {
#           "gravitationalConstant": -20000,
#           "springLength": 250
#         },
#         "minVelocity": 0.75
#       }
#     }
#     ''')

#     for node, data in G.nodes(data=True):
#         group = data.get("bipartite", -1)
#         if group == 0:
#             net.add_node(node, label=node, color="#FF5733")
#         elif group == 1:
#             net.add_node(node, label=node, color="#3498DB")
#         else:
#             net.add_node(node, label=node, color="#95A5A6")

#     for source, target in G.edges():
#         net.add_edge(source, target)

#     tmp_dir = tempfile.mkdtemp()
#     html_path = os.path.join(tmp_dir, "graph.html")
#     net.save_graph(html_path)

#     # JS code to capture node click and store in a file via Streamlit's query params
#     js_code = """
#     <script type="text/javascript">
#     const nodes = window.network.body.data.nodes;
#     network.on("click", function(params) {
#         if (params.nodes.length > 0) {
#             const selectedNode = params.nodes[0];
#             const form = document.createElement('form');
#             form.method = 'POST';
#             form.action = '/selected_node';
#             const input = document.createElement('input');
#             input.type = 'hidden';
#             input.name = 'node';
#             input.value = selectedNode;
#             form.appendChild(input);
#             document.body.appendChild(form);
#             form.submit();
#         }
#     });
#     </script>
#     """

#     with open(html_path, "a", encoding="utf-8") as f:
#         f.write(js_code)

#     # Read selected node if exists
#     selected_node = None
#     if os.path.exists(selected_node_path):
#         with open(selected_node_path, "r", encoding="utf-8") as f:
#             selected_node = f.read().strip()

#     return html_path, selected_node

# def save_selected_node(node):
#     with open(selected_node_path, "w", encoding="utf-8") as f:
#         f.write(node)

# def clear_selected_node():
#     if os.path.exists(selected_node_path):
#         os.remove(selected_node_path)






# import tempfile
# import os
# from pyvis.network import Network

# def display_graph(G):
#     net = Network(height="600px", width="100%", notebook=False, bgcolor="#ffffff", font_color="black")

#     for node, data in G.nodes(data=True):
#         group = data.get("bipartite", -1)
#         if group == 0:
#             net.add_node(node, label=node, color="#FF5733")
#         elif group == 1:
#             net.add_node(node, label=node, color="#3498DB")
#         else:
#             net.add_node(node, label=node, color="#95A5A6")

#     for source, target in G.edges():
#         net.add_edge(source, target)

#     # Générer HTML temporaire
#     tmp_dir = tempfile.mkdtemp()
#     html_path = os.path.join(tmp_dir, "graph.html")
#     net.save_graph(html_path)

#     # Injecter un petit script JS pour détecter le clic
#     with open(html_path, "r", encoding="utf-8") as f:
#         html = f.read()

#     injected_js = """
#     <script>
#     function waitForNetwork() {
#         if (window.network && window.network.body && window.network.body.nodes) {
#             network.on("click", function(params) {
#                 if (params.nodes.length > 0) {
#                     const nodeId = params.nodes[0];
#                     window.parent.postMessage({ type: 'NODE_CLICK', node: nodeId }, '*');
#                 }
#             });
#         } else {
#             setTimeout(waitForNetwork, 100);
#         }
#     }
#     waitForNetwork();
#     </script>
#     """

#     html += injected_js

#     with open(html_path, "w", encoding="utf-8") as f:
#         f.write(html)

#     return html_path



# import tempfile
# import os
# from pyvis.network import Network

# def display_graph(G):
#     net = Network(height="600px", width="100%", notebook=False, bgcolor="#ffffff", font_color="black")

#     for node, data in G.nodes(data=True):
#         group = data.get("bipartite", -1)
#         if group == 0:
#             net.add_node(node, label=node, color="#FF5733")
#         elif group == 1:
#             net.add_node(node, label=node, color="#3498DB")
#         else:
#             net.add_node(node, label=node, color="#95A5A6")

#     for source, target in G.edges():
#         net.add_edge(source, target)

#     # Générer HTML temporaire
#     tmp_dir = tempfile.mkdtemp()
#     html_path = os.path.join(tmp_dir, "graph.html")
#     net.save_graph(html_path)

#     # Injecter un petit script JS pour détecter le clic
#     with open(html_path, "r", encoding="utf-8") as f:
#         html = f.read()

#     injected_js = """
#     <script>
#     function waitForNetwork() {
#         if (window.network && window.network.body && window.network.body.nodes) {
#             network.on("click", function(params) {
#                 if (params.nodes.length > 0) {
#                     const nodeId = params.nodes[0];
#                     window.parent.postMessage({ type: 'NODE_CLICK', node: nodeId }, '*');
#                 }
#             });
#         } else {
#             setTimeout(waitForNetwork, 100);
#         }
#     }
#     waitForNetwork();
#     </script>
#     """

#     html += injected_js

#     with open(html_path, "w", encoding="utf-8") as f:
#         f.write(html)

#     return html_path


# from pyvis.network import Network
# import tempfile
# import os

# def display_graph(G):
#     """returns HTML path to interactive graph with clickable nodes"""

#     net = Network(height="600px", width="100%", notebook=False, bgcolor="#000c15", font_color="white")

#     for node, data in G.nodes(data=True):
#         group = data.get("bipartite", -1)
#         if group == 0:  # concept
#             net.add_node(node, label=node, color="#FF5733")
#         elif group == 1:  # document
#             net.add_node(node, label=node, color="#3498DB")
#         else:
#             net.add_node(node, label=node, color="#95A5A6")

#     for source, target in G.edges():
#         net.add_edge(source, target)

#     # HTML injection
#     tmp_dir = tempfile.mkdtemp()
#     html_path = os.path.join(tmp_dir, "graph.html")
#     net.save_graph(html_path)

#     custom_js = """
#     <script>
#     function sendNodeClickToStreamlit(nodeId) {
#         const msg = { clicked_node: nodeId };
#         window.parent.postMessage(msg, "*");
#     }

#     setTimeout(function() {
#         if (window.network) {
#             network.on("click", function (params) {
#                 if (params.nodes.length > 0) {
#                     const nodeId = params.nodes[0];
#                     sendNodeClickToStreamlit(nodeId);
#                 }
#             });
#         }
#     }, 500);
#     </script>
#     """

#     with open(html_path, "a", encoding="utf-8") as f:
#         f.write(custom_js)

#     return html_path


# from pyvis.network import Network
# import tempfile
# import os

# # the network class from the pyvis library is used to generate interactive visualizations of a graph
# # the tempfile library is used to generate a temporay file, here a temporary html file

# def display_graph(G):
#     """this function returns an interactive visualization of a graph

#     Args:
#         G (networkx.Graph): a graph 

#     Returns:
#         str: the html path to the graph display
#     """
#     # net = Network(height="600px", width="100%", notebook=False)
#     net = Network(height="600px", width="100%", notebook=False, bgcolor="#ffffff", font_color="black")

#     for node, data in G.nodes(data=True):
#         group = data.get("bipartite", -1)
#         if group == 0:  # concept
#             net.add_node(node, label=node, color="#FF5733")  # orange/rouge
#         elif group == 1:  # document
#             net.add_node(node, label=node, color="#3498DB")  # bleu
#         else:
#             net.add_node(node, label=node, color="#95A5A6")  # gris par défaut

#     for source, target in G.edges():
#         net.add_edge(source, target)

#     tmp_dir = tempfile.mkdtemp()
#     html_path = os.path.join(tmp_dir, "graph.html")
#     net.save_graph(html_path)

#     # net.from_nx(G)
#     # tmp_dir = tempfile.mkdtemp()
#     # html_path = os.path.join(tmp_dir, "graph.html")
#     # net.save_graph(html_path)

#     return html_path



