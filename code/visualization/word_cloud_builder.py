# -*- coding: utf-8 -*-

############################
# Word cloud builder       #
#                          #
# Last update : 2025/07/21 #
############################

from wordcloud import WordCloud
import matplotlib.pyplot as plt
import spacy
from spacy.lang.fr.stop_words import STOP_WORDS

# Charge le modèle linguistique français
nlp = spacy.load("fr_core_news_sm")

def preprocess_text(text):
    doc = nlp(text)
    tokens = [
        token.lemma_.lower()
        for token in doc
        if token.is_alpha and token.lemma_.lower() not in STOP_WORDS
    ]
    return " ".join(tokens)

def generate_wordcloud(text, max_words=10):
    cleaned_text = preprocess_text(text)
    wc = WordCloud(
        width=800,
        height=400,
        background_color=None,
        mode="RGBA",
        colormap="magma",
        max_words=max_words
    )
    wc.generate(cleaned_text)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")

    return fig, wc




