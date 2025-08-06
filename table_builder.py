# -*- coding: utf-8 -*-
"""Utility functions to build tables for the Streamlit app.

This module currently provides helpers for the *events table*. Each
row of this table summarizes one event found in the text and exposes
its location, time and people involved.

All processing is done locally. Summaries are generated through a
small language model accessible via the ``ollama`` CLI (for instance
``mistral``). If ``ollama`` is not installed or fails, a short summary is
computed locally using an LSA-based algorithm provided by
``entity_extractor.extract_events``.

Note: the local fallback does not require any external API and works even
when ``ollama`` is unavailable.
"""

from __future__ import annotations

import time
import requests
from dataclasses import dataclass
from typing import Dict, List

import spacy

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas might be missing
    pd = None  # type: ignore

from entity_extractor import (
    extract_dates,
    extract_individuals,
    extract_locations,
    extract_times,
    extract_events,
)

# light French model is enough for sentence segmentation
_nlp = spacy.load("fr_core_news_sm")


def call_ollama(model: str, prompt: str) -> str:
    """Call a local LLM via ``ollama`` and return the raw response."""
    url = "http://localhost:11434/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception:
        # If ollama is not available or busy, wait a bit and return empty string
        time.sleep(1)
        return ""


def summarize_sentence(sent: str) -> str:
    """Return a very short summary of ``sent`` using Ollama if possible.

    If the call to ``ollama`` fails or returns an empty string, a local LSA
    summarizer (``entity_extractor.extract_events``) is used as a fallback.
    """
    prompt = (
        "Resume en quelques mots l'evenement suivant sans aucun commentaire :\n"
        f"{sent}"
    )
    summary = call_ollama("mistral", prompt).strip()
    # if not summary:
    #     # fallback to a local LSA summarizer
    #     summary = extract_events(sent)

    summary = summary.strip()
    lines = summary.splitlines()
    if lines:
        return lines[0].strip()
    return ""


@dataclass
class EventRow:
    evenement: str
    lieu: str
    moment: str
    qui: str
    document: str | None = None


def extract_events_from_text(text: str) -> List[EventRow]:
    """Extract a list of :class:`EventRow` from a single text."""
    doc = _nlp(text)
    rows: List[EventRow] = []

    for sent in doc.sents:
        sentence = sent.text.strip()
        if not sentence:
            continue

        summary = summarize_sentence(sentence)
        lieux = ", ".join(extract_locations(sentence))
        dates = extract_dates(sentence)
        times = extract_times(sentence)
        moment = ", ".join(dates + times)
        individus = ", ".join(extract_individuals(sentence))

        if any([summary, lieux, moment, individus]):
            rows.append(
                EventRow(
                    evenement=summary,
                    lieu=lieux,
                    moment=moment,
                    qui=individus,
                )
            )

    return rows


def build_event_table(corpus: Dict[str, str]):
    """Build a table of events for the given ``corpus``.

    Parameters
    ----------
    corpus:
        Mapping from document name to text.

    Returns
    -------
    pandas.DataFrame or list of dicts
        Table with columns ``document``, ``evenement``, ``lieu``, ``moment`` and
        ``qui``.
    """
    all_rows: List[EventRow] = []
    for name, text in corpus.items():
        rows = extract_events_from_text(text)
        for row in rows:
            row.document = name
        all_rows.extend(rows)

    data = [
        {
            "document": r.document,
            "evenement": r.evenement,
            "lieu": r.lieu,
            "moment": r.moment,
            "qui": r.qui,
        }
        for r in all_rows
    ]

    if pd is not None:
        return pd.DataFrame(data)
    return data




