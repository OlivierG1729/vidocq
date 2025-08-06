# Application VIDOCQ (VIsualisation de DOCuments par Questionnements

L'application VIDOCQ propose différents visuels destinés à appréhender de façon rapide un corpus de documents.

Actuellement, l'application propose deux fonctionnalités :

**1. Recherche de concepts dans un corpus de documents et visualisation par graphe dynamique** 
  - l'utilisateur importe un corpus de documents. Pour le moment, ces documents sont nécessairement des fichiers .txt, mais à terme l'application prendra aussi en compte des ficheirs aux formats .csv et .pdf
  - il renseigne ensuite les concepts par des mots clés séparés par des virgules
  - il choisit une méthode de recherche, et calibre les paramètres attachés à la méthode sélectionnée
  - un graphe apparait alors, composés de deux types de noeuds : les documents et les concepts. Un noeud-concept et un noeud-document sont reliés par une arête si et seulement si ce concept apparaît dans ce document
  - ce graphe est dynamique, il est possible de déplacer ses noeuds, agir la taille des arêtes etc.
  - il est possible de sauvegarder le graphe, au format .html pour une version dynamique ou au format .png pour une version statique

**2. Word clouds d'un corpus de documents**

  - l'utilisateur importe un corpus de document, pour le moment au format .txt, mais à terme il sera possible d'importer également des fichiers .csv et .pdf
  - il sélectionne un document dans ce corpus
  - puis il décide di nombre de mots qu'il veut voir appraître dans le nuage
  - un nuage de mots apparaît. Un prétraitement du texte (tokenisation, stop words, stemming, lemmatisation) permet de supprimer les mots non signifiants ("la", "le", "des", "avec", "et", etc.) et les redondances ("ami" et "amies", "détecter", et "détection" etc.)

  - 
