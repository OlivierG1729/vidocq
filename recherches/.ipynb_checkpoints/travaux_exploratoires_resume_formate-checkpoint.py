
# -*- coding: utf-8 -*-


##############################################
# Explorations about formated synthese       #
#                                            #
# Last update : 2025/07/22                   #
##############################################

import spacy

nlp = spacy.load("fr_core_news_md")

def extract_quadruplets(text):
    doc = nlp(text)
    events = []

    for sent in doc.sents:
        lieu = [ent.text for ent in sent.ents if ent.label_ == "LOC"]
        moment = [ent.text for ent in sent.ents if ent.label_ in ["DATE", "TIME"]]
        individus = [ent.text for ent in sent.ents if ent.label_ == "PER"]
        action = [token.lemma_ for token in sent if token.pos_ == "VERB"]

        if action:
            events.append({
                "événement": ", ".join(action),
                "où": ", ".join(lieu),
                "quand": ", ".join(moment),
                "qui": ", ".join(individus)
            })

    return events
