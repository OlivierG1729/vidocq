# -*- coding: utf-8 -*-

############################
# Entities extractor       #
#                          #
# Last update : 2025/07/22 #
############################


import spacy
import re
from spacy.lang.fr.stop_words import STOP_WORDS
from dateparser.search import search_dates
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from dateparser.search import search_dates


nlp = spacy.load("fr_core_news_md")  # Ou "lg" pour plus de puissance

EXCLUSION_TERMS = {
    "affaire", "projet", "mission", "procès", "ministère", "dossier",
    "groupe", "commission", "association", "organisation",
    "entreprise", "rapport", "syndicat", "déclaration", "campagne"
}

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
import re

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


text = "Le 21 juin 2023 à 9h15, Jean Dupont est arrivé au 18 rue des Lilas, Paris. Il a assisté à une réunion confidentielle dans le cadre de l’affaire X."

print("Individus :", extract_individuals(text))
print("Adresses :", extract_addresses(text))
print("Dates :", extract_dates(text))
print("Horaires :", extract_times(text))
print("Lieux :", extract_locations(text))
print("Résumé d’événement :", extract_events(text))



# text = """
# Jean a quitté son domicile à 9h15. Il est revenu en fin de matinée, puis reparti vers minuit.
# Martine a été vue au crépuscule près de la gare, l'agent L était actif en soirée.
# """

# print("Horaires détectés :", extract_times(text))
