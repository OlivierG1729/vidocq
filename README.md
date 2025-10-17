# VIDOCQ – Gestion des index

Cette version de l'application maintient désormais plusieurs artefacts calculés afin d'accélérer les analyses :

- un index inversé (token → documents),
- une matrice TF-IDF et son vectoriseur associé,
- des embeddings sémantiques générés via `SentenceTransformer`.

## Où sont stockés les fichiers ?

Les index sont persistés dans le dossier [`output/index_cache/`](output/index_cache/). On y trouve notamment :

- `documents.json` et `clean_documents.json` : textes bruts et normalisés ;
- `inverted_index.json` : index inversé ;
- `tfidf_vectorizer.joblib` & `tfidf_matrix.npz` : vectoriseur et matrice TF-IDF ;
- `embeddings.npy` : embeddings sémantiques ;
- `metadata.json` : hachages des documents suivis.

Le cache des entités (résultats de `entity_extractor`) est conservé dans [`output/entity_cache.json`](output/entity_cache.json).

## Comment régénérer les index ?

Les index se mettent à jour automatiquement lorsque de nouveaux fichiers sont importés dans l'application. Pour forcer une régénération manuelle, supprimez simplement les fichiers du dossier `output/index_cache/` (et `output/entity_cache.json` si nécessaire), puis rechargez vos documents dans l'interface Streamlit : les artefacts seront reconstruits à la volée.

