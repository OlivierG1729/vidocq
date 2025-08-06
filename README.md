# Application VIDOCQ (VIsualisation de DOCuments par Questionnements

L'application VIDOCQ propose différents visuels destinés à appréhender de façon rapide un corpus de documents.

Actuellement, l'application propose deux fonctionnalités :

**1. Recherche de concepts dans un corpus de documents et visualisation par graphe dynamique** 

L'utilisateur importe un corpus de documents (fichiers .txt pour le moment, à venir : .csv et .pdf), renseigne des concepts par des mots-clés séparés par des virgules. Il choisit également une méthode de recherche, et ajuste les valeurs des paramètres de cette méthode. Un graphe apparait alors, composés de deux types de noeuds : les documents et les concepts. Un noeud-concept et un noeud-document sont reliés par une arête si et seulement si ce concept apparaît dans ce document. Ce graphe est dynamique, il est possible de déplacer ses noeuds, agir la taille des arêtes etc. Il est possible de le sauvegarder au format .html (pour une version dynamique) ou .png (pour une version statique).

**2. Word cloud d'un corpus de documents**

L'utilisateur importe un corpus de documents (fichiers .txt pour le moment, à venir : .csv et .pdf), sélectionne un document dans ce corpus. Un nuage de mots apparaît, permettant une vision syntéhtique du texte.Le nombre de mots du nuage est ajustable. Un prétraitement du texte (tokenisation, stop words, stemming, lemmatisation) permet de supprimer les mots non signifiants ("la", "le", "des", "avec", "et", etc.) et les redondances ("ami" et "amies", "détecter", et "détection" etc.). 
