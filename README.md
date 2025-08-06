# Application VIDOCQ (VIsualisation de DOCuments par Questionnements


![Exemple de capture d’écran](logos/vidocq_logo.png)



L'application VIDOCQ propose différents visuels destinés à appréhender de façon rapide un corpus de documents.

Actuellement, l'application propose deux fonctionnalités :

**1. Recherche de concepts dans un corpus de documents et visualisation par graphe dynamique** 

L'utilisateur importe un corpus de documents (fichiers .txt pour le moment, à venir : .csv et .pdf), renseigne des concepts par des mots-clés séparés par des virgules. Il choisit également une méthode de recherche, et ajuste les valeurs des paramètres de cette méthode. Un graphe apparait alors, composés de deux types de noeuds : les documents et les concepts. Un noeud-concept et un noeud-document sont reliés par une arête si et seulement si ce concept apparaît dans ce document. Ce graphe est dynamique, il est possible de déplacer ses noeuds, agir la taille des arêtes etc. Il est possible de le sauvegarder au format .html (pour une version dynamique) ou .png (pour une version statique).

![Exemple de capture d’écran](images/graphe_exemple.png)


**2. Word cloud d'un corpus de documents**

L'utilisateur importe un corpus de documents (fichiers .txt pour le moment, à venir : .csv et .pdf), sélectionne un document dans ce corpus. Un nuage de mots apparaît, permettant une vision syntéhtique du texte.Le nombre de mots du nuage est ajustable. Un prétraitement du texte (tokenisation, stop words, stemming, lemmatisation) permet de supprimer les mots non signifiants ("la", "le", "des", "avec", "et", etc.) et les redondances ("ami" et "amies", "détecter", et "détection" etc.). 

![Exemple de capture d’écran](images/nuage_mots_exemple.png)


**A venir :** l'application proposera prochainement une nouvelle fonctionnalité, dédiée à la visualisation cartographique d'événements. Il s'agit, à partir d'un document du corpus, d'extraire tous les événements relatés par le document, de détecter les lieux, moments, et individus impliqués dans ces événements. Ces événements seront alors visualisables sur une carte type OpenStreetMap. Il est nécessaire pour que cela fonctionne de disposer des adresses exactes des différents événements, ou à défaut des noms des communes dans lesquelles ces événements se sont produits (dans ce derner cas, et en l'absence d'informations supplémentaires, l'événement sera localisé sur la mairie de la commune). L'application pourra à terme s'appuyer sur d'autres types d'éléments localisants, comme le nom d'un monument ou d'un lieu public. Il est également prévu que l'utilisateur puisse lui-même renseigner l'adresse s'il en dispose. Par exemple, si le texte fait référence au domicile de M.X, alors l'utilisateur pourra renseigner dans une fenêtre de saisie l'adresse du domicile de M.X de façon à rendre possible sa visualisation sur la carte.






