# -*- coding: utf-8 -*-

############################
# Entities extractor       #
#                          #
# Last update : 2025/07/22 #
############################


import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import spacy
import re
from spacy.lang.fr.stop_words import STOP_WORDS
from dateparser.search import search_dates
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer


nltk_model = "fr_core_news_md"
nlp = spacy.load(nltk_model)  # Ou "lg" pour plus de puissance

CACHE_PATH = Path("output/entity_cache.json")

EXCLUSION_TERMS = {
    "affaire", "projet", "mission", "procès", "ministère", "dossier",
    "groupe", "commission", "association", "organisation",
    "entreprise", "rapport", "syndicat", "déclaration", "campagne"
}


@dataclass
class EntityRecord:
    individuals: list
    locations: list
    addresses: list
    dates: list
    times: list
    summary: str
    hash: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "individuals": self.individuals,
            "locations": self.locations,
            "addresses": self.addresses,
            "dates": self.dates,
            "times": self.times,
            "summary": self.summary,
            "hash": self.hash,
        }


class EntityCache:
    def __init__(self, path: Path = CACHE_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, object]] = self._load()

    def _load(self) -> Dict[str, Dict[str, object]]:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._cache, fh, ensure_ascii=False, indent=2)

    def get(self, document_id: str) -> Optional[Dict[str, object]]:
        return self._cache.get(document_id)

    def store(self, document_id: str, record: EntityRecord) -> None:
        self._cache[document_id] = record.to_dict()
        self._save()

    def get_or_create(self, document_id: str, document_hash: str, text: str) -> Dict[str, object]:
        cached = self.get(document_id)
        if cached and cached.get("hash") == document_hash:
            return cached

        record = extract_all_entities(text)
        record.hash = document_hash
        self.store(document_id, record)
        return record.to_dict()

def is_valid_person(name):
    name_clean = name.strip()

    # ⛔ Exclure les noms trop courts (ex : "X", "Y", "Z")
    if len(name_clean.split()) < 2 or len(name_clean) < 3:
        return False

    # ⛔ Exclure les expressions contenant des termes non humains
    if any(term in name_clean.lower() for term in EXCLUSION_TERMS):
        return False

    # ⛔ Exclure les noms contenant des caractères non alphabétiques ou symboles
    if re.search(r"[0-9{}\[\]()<>*%$@!#^~]", name_clean):
        return False

    # ⛔ Exclure les noms entièrement en majuscules (souvent institutions)
    if name_clean.isupper():
        return False

    # ✅ Si tout est bon, c’est probablement un individu humain
    return True

# ✅ Extraction des individus
def extract_individuals(text):
    doc = nlp(text)
    individuals = set()
    for ent in doc.ents:
        if ent.label_ == "PER":
            name = ent.text.strip()
            if is_valid_person(name):
                individuals.add(name)
    return list(individuals)

# ✅ Extraction des lieux (noms de lieux ou adresses partielles)
def extract_locations(text):
    doc = nlp(text)
    locations = set()
    for ent in doc.ents:
        if ent.label_ in ["LOC", "GPE", "FAC"]:
            locations.add(ent.text.strip())
    return list(locations)

# ✅ Extraction des adresses (via regex ou NER sémantique)
def extract_addresses(text):
    voie_keywords = (
        "rue|avenue|boulevard|place|impasse|allée|chemin|quai|route|cours|square|esplanade|voie|passage|pont|villa"
    )

    # 📍 Motif 1 : adresse avec numéro
    pattern_numbered = rf"\b\d{{1,4}}[\s\w\-]*\s(?:{voie_keywords})[\s\w\-]*\b"

    # 📍 Motif 2 : type de voie + nom (min 1 mot après le type)
    pattern_nonnumbered = rf"\b(?:{voie_keywords})\s+\w[\w\s\-]{2,}\b"

    matches1 = re.findall(pattern_numbered, text, flags=re.IGNORECASE)
    matches2 = re.findall(pattern_nonnumbered, text, flags=re.IGNORECASE)

    addresses = set(matches1 + matches2)
    cleaned = [addr.strip().title() for addr in addresses if addr.lower() != "rue"]

    return cleaned

# ✅ Extraction des dates
def extract_dates(text):
    found = search_dates(text, languages=["fr"])
    if found:
        return list(set(date.strftime("%Y-%m-%d") for label, date in found if date.year))
    return []

# ✅ Extraction des horaires

def extract_times(text):
    """
    Extrait les horaires explicites et flous d’un texte.
    Renvoie une liste d’horaires au format texte (ex : '9h15', 'vers 6h').
    """

    horaires = set()

    # 🕰️ 1. Horaires classiques : "9h", "14h05", "07h30"
    pattern_precis = r"\b([01]?\d|2[0-3])h([0-5]\d)?\b"
    matches = re.findall(pattern_precis, text)

    for h, m in matches:
        if m:
            horaires.add(f"{h}h{m}")
        else:
            horaires.add(f"{h}h")

    # 🌤️ 2. Expressions floues et approximatives
    flou_patterns = {
        r"\bmatinée\b": "9h",
        r"\bfin de matinée\b": "11h",
        r"\bà midi\b": "12h",
        r"\bmilieu de journée\b": "12h",
        r"\baprès-midi\b": "15h",
        r"\bfin d'après-midi\b": "17h",
        r"\ben soirée\b": "20h",
        r"\bà l’aube\b": "6h",
        r"\bau crépuscule\b": "19h30",
        r"\bvers midi\b": "12h",
        r"\bvers minuit\b": "00h",
        r"\bpetite matinée\b": "7h"
    }

    for pattern, estimation in flou_patterns.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            horaires.add(f"≈ {estimation}")

    return sorted(horaires)


# ✅ Extraction des événements (résumé court)
def extract_events(text, nb_sentences=1):
    parser = PlaintextParser.from_string(text, Tokenizer("french"))
    summarizer = LsaSummarizer()
    summarizer.stop_words = STOP_WORDS
    summary = summarizer(parser.document, nb_sentences)
    return " ".join(str(s) for s in summary)


def extract_all_entities(text: str, nb_sentences: int = 1) -> EntityRecord:
    return EntityRecord(
        individuals=extract_individuals(text),
        locations=extract_locations(text),
        addresses=extract_addresses(text),
        dates=extract_dates(text),
        times=extract_times(text),
        summary=extract_events(text, nb_sentences),
    )


_ENTITY_CACHE: Optional[EntityCache] = None


def get_entity_cache() -> EntityCache:
    global _ENTITY_CACHE
    if _ENTITY_CACHE is None:
        _ENTITY_CACHE = EntityCache()
    return _ENTITY_CACHE


__all__ = [
    "EntityCache",
    "EntityRecord",
    "extract_all_entities",
    "extract_addresses",
    "extract_dates",
    "extract_events",
    "extract_individuals",
    "extract_locations",
    "extract_times",
    "get_entity_cache",
]
