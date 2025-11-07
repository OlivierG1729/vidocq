"""Utilities for building and caching document indexes.

This module centralises the creation of:

* an inverted index (token → list of documents),
* a TF–IDF representation of the corpus,
* semantic embeddings generated with ``SentenceTransformer``.

The goal is to build the heavy artefacts once and reuse them across the
application. The indexes are stored on disk inside ``output/index_cache`` and
are automatically invalidated whenever a new document is detected or an
existing file is modified.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import joblib
import numpy as np
from scipy import sparse
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from data_loader import load_documents


# ===============================
# FONCTIONS UTILITAIRES
# ===============================

def _split_into_passages(text: str, max_sentences: int = 5) -> list[str]:
    """Découpe un texte en passages de n phrases maximum."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    passages = []
    for i in range(0, len(sentences), max_sentences):
        passages.append(" ".join(sentences[i:i + max_sentences]))
    return passages


CACHE_DIR = Path("output/index_cache")
DOC_TEXTS_FILE = CACHE_DIR / "documents.json"
CLEAN_TEXTS_FILE = CACHE_DIR / "clean_documents.json"
INVERTED_INDEX_FILE = CACHE_DIR / "inverted_index.json"
METADATA_FILE = CACHE_DIR / "metadata.json"
DOC_ORDER_FILE = CACHE_DIR / "doc_order.json"
TFIDF_VECTORIZER_FILE = CACHE_DIR / "tfidf_vectorizer.joblib"
TFIDF_MATRIX_FILE = CACHE_DIR / "tfidf_matrix.npz"
EMBEDDINGS_FILE = CACHE_DIR / "embeddings.npy"

MODEL_NAME = "paraphrase-MiniLM-L6-v2"


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _compute_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _normalise_text(text: str) -> str:
    """Light normalisation used throughout the indexing pipeline."""
    import unicodedata

    if not isinstance(text, str):
        text = str(text)

    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ===============================
# STRUCTURE DES DONNÉES
# ===============================

@dataclass
class IndexData:
    documents: Dict[str, str]
    clean_documents: Dict[str, str]
    doc_order: List[str]
    inverted_index: Dict[str, List[str]]
    tfidf_vectorizer: TfidfVectorizer
    tfidf_matrix: sparse.csr_matrix
    embeddings: np.ndarray
    document_hashes: Dict[str, str]
    passages: Optional[List[str]] = None
    passage_to_doc: Optional[List[str]] = None

    def as_tensor(self):
        import torch
        return torch.from_numpy(self.embeddings)


# ===============================
# GESTIONNAIRE D'INDEX
# ===============================

class IndexManager:
    def __init__(self) -> None:
        _ensure_cache_dir()
        self._model: Optional[SentenceTransformer] = None
        self._index_data: Optional[IndexData] = None
        self._metadata: Dict[str, Dict[str, str]] = self._load_metadata()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def ensure_indexes(self, files: Iterable) -> IndexData:
        documents = load_documents(files)
        document_hashes = {name: _compute_hash(text) for name, text in documents.items()}

        if not self._needs_rebuild(document_hashes):
            if self._index_data is None:
                self._index_data = self._load_from_disk()
            return self._index_data

        index_data = self._build_indexes(documents, document_hashes)
        self._save_to_disk(index_data)
        self._metadata = {doc: {"hash": digest} for doc, digest in document_hashes.items()}
        self._save_metadata()
        self._index_data = index_data
        return index_data

    def get_index_data(self) -> Optional[IndexData]:
        if self._index_data is None and METADATA_FILE.exists():
            self._index_data = self._load_from_disk()
        return self._index_data

    def _needs_rebuild(self, new_hashes: Dict[str, str]) -> bool:
        if set(new_hashes.keys()) != set(self._metadata.keys()):
            return True
        for name, digest in new_hashes.items():
            if self._metadata.get(name, {}).get("hash") != digest:
                return True
        return False

    def _build_indexes(self, documents: Dict[str, str], document_hashes: Dict[str, str]) -> IndexData:
        # --- Nettoyage léger des textes
        clean_documents = {name: _normalise_text(text) for name, text in documents.items()}
        doc_order = list(documents.keys())

        # --- Création de l'index inversé
        inverted_index: Dict[str, List[str]] = {}
        for doc_name, text in clean_documents.items():
            for token in text.split():
                inverted_index.setdefault(token, set()).add(doc_name)
        inverted_index = {token: sorted(list(doc_ids)) for token, doc_ids in inverted_index.items()}

        # --- Construction du TF-IDF global
        vectorizer = TfidfVectorizer(ngram_range=(1, 3))
        tfidf_matrix = vectorizer.fit_transform([clean_documents[name] for name in doc_order])

        # --- 🧩 Segmentation en passages
        passages = []
        passage_to_doc = []
        for doc_name, text in documents.items():
            segments = _split_into_passages(text)
            passages.extend(segments)
            passage_to_doc.extend([doc_name] * len(segments))

        # --- Encodage sémantique sur les passages
        embeddings = self.model.encode(
            passages,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # --- Création de l'objet enrichi
        return IndexData(
            documents=documents,
            clean_documents=clean_documents,
            doc_order=doc_order,
            inverted_index=inverted_index,
            tfidf_vectorizer=vectorizer,
            tfidf_matrix=tfidf_matrix,
            embeddings=embeddings,
            document_hashes=document_hashes,
            passages=passages,
            passage_to_doc=passage_to_doc,
        )

    def _save_to_disk(self, index_data: IndexData) -> None:
        _ensure_cache_dir()
        DOC_TEXTS_FILE.write_text(json.dumps(index_data.documents, ensure_ascii=False, indent=2), encoding="utf-8")
        CLEAN_TEXTS_FILE.write_text(json.dumps(index_data.clean_documents, ensure_ascii=False, indent=2), encoding="utf-8")
        DOC_ORDER_FILE.write_text(json.dumps(index_data.doc_order, ensure_ascii=False, indent=2), encoding="utf-8")
        INVERTED_INDEX_FILE.write_text(json.dumps(index_data.inverted_index, ensure_ascii=False, indent=2), encoding="utf-8")
        np.save(EMBEDDINGS_FILE, index_data.embeddings)
        joblib.dump(index_data.tfidf_vectorizer, TFIDF_VECTORIZER_FILE)
        sparse.save_npz(TFIDF_MATRIX_FILE, index_data.tfidf_matrix)

        # 🆕 Sauvegarde des passages
        passages_file = CACHE_DIR / "passages.json"
        mapping_file = CACHE_DIR / "passage_to_doc.json"
        if index_data.passages is not None and index_data.passage_to_doc is not None:
            passages_file.write_text(json.dumps(index_data.passages, ensure_ascii=False, indent=2), encoding="utf-8")
            mapping_file.write_text(json.dumps(index_data.passage_to_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_from_disk(self) -> IndexData:
        documents = json.loads(DOC_TEXTS_FILE.read_text(encoding="utf-8")) if DOC_TEXTS_FILE.exists() else {}
        clean_documents = json.loads(CLEAN_TEXTS_FILE.read_text(encoding="utf-8")) if CLEAN_TEXTS_FILE.exists() else {}
        doc_order = json.loads(DOC_ORDER_FILE.read_text(encoding="utf-8")) if DOC_ORDER_FILE.exists() else []
        inverted_index = json.loads(INVERTED_INDEX_FILE.read_text(encoding="utf-8")) if INVERTED_INDEX_FILE.exists() else {}
        embeddings = np.load(EMBEDDINGS_FILE, allow_pickle=False) if EMBEDDINGS_FILE.exists() else np.array([])
        vectorizer: TfidfVectorizer = joblib.load(TFIDF_VECTORIZER_FILE) if TFIDF_VECTORIZER_FILE.exists() else TfidfVectorizer()
        tfidf_matrix = sparse.load_npz(TFIDF_MATRIX_FILE) if TFIDF_MATRIX_FILE.exists() else sparse.csr_matrix((0, 0))
        document_hashes = {name: meta["hash"] for name, meta in self._metadata.items()}

        # 🆕 Lecture des passages
        passages_file = CACHE_DIR / "passages.json"
        mapping_file = CACHE_DIR / "passage_to_doc.json"
        passages, passage_to_doc = [], []
        if passages_file.exists() and mapping_file.exists():
            passages = json.loads(passages_file.read_text(encoding="utf-8"))
            passage_to_doc = json.loads(mapping_file.read_text(encoding="utf-8"))

        return IndexData(
            documents=documents,
            clean_documents=clean_documents,
            doc_order=doc_order,
            inverted_index=inverted_index,
            tfidf_vectorizer=vectorizer,
            tfidf_matrix=tfidf_matrix,
            embeddings=embeddings,
            document_hashes=document_hashes,
            passages=passages,
            passage_to_doc=passage_to_doc,
        )

    def _load_metadata(self) -> Dict[str, Dict[str, str]]:
        if METADATA_FILE.exists():
            with open(METADATA_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _save_metadata(self) -> None:
        with open(METADATA_FILE, "w", encoding="utf-8") as fh:
            json.dump(self._metadata, fh, ensure_ascii=False, indent=2)


# ===============================
# SINGLETON GLOBAL
# ===============================

_INDEX_MANAGER: Optional[IndexManager] = None


def get_index_manager() -> IndexManager:
    global _INDEX_MANAGER
    if _INDEX_MANAGER is None:
        _INDEX_MANAGER = IndexManager()
    return _INDEX_MANAGER


__all__ = ["IndexData", "IndexManager", "get_index_manager"]
