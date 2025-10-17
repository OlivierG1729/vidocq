"""Utilities to convert extracted entities into an interactive map of events.

This module centralises the logic that geocodes textual locations and builds a
Folium map that can be embedded inside the Streamlit application.  The goal is
that the Streamlit layer only has to provide the raw entity payloads coming
from :mod:`entity_extractor` and receive an HTML fragment representing the map.
"""

from __future__ import annotations

import json
import re
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar

import folium
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from entity_extractor import (
    extract_dates,
    extract_events,
    extract_individuals,
    extract_times,
)

_GEOCODE_CACHE_PATH = Path("output/geocode_cache.json")
_GEOCODE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

_LLM_MODEL = "mistral:7b-instruct-q4_K_M"
_LLM_ENDPOINT = "http://localhost:11434/api/generate"
_MAX_CONTEXT_CHARS = 2000

_LLM_DETAILS_CACHE: Dict[Tuple[str, str], Tuple[str, List[str], str]] = {}


@dataclass
class EventMarker:
    """Representation of a location associated to an event in a document."""

    document: str
    location_label: str
    latitude: float
    longitude: float
    summary: str
    individuals: Sequence[str]
    moment: str

    def _join(self, values: Sequence[str]) -> str:
        cleaned = [value.strip() for value in values if value and value.strip()]
        return ", ".join(cleaned) if cleaned else "—"

    def individuals_text(self) -> str:
        """Return a human readable list of individuals."""

        return self._join(self.individuals)

    def moment_text(self) -> str:
        """Return the textual description of when the event occurred."""

        if isinstance(self.moment, str):
            moment = self.moment.strip()
            return moment or "—"
        return "—"

    def popup_html(self) -> str:
        """Return an HTML snippet describing the marker."""

        people = self.individuals_text()
        moment = self.moment_text()
        summary = self.summary or "—"

        return (
            f"<strong>{self.document}</strong><br/>"
            f"<em>{self.location_label}</em><br/>"
            f"<div style='margin-top:0.5em'>"
            f"<strong>Résumé :</strong> {summary}<br/>"
            f"<strong>Personnes :</strong> {people}<br/>"
            f"<strong>Moment :</strong> {moment}"
            "</div>"
        )

    def tooltip_html(self) -> str:
        """Return a concise HTML snippet for hover tooltips."""

        return (
            "<div style='line-height:1.4em'>"
            f"<strong>{self.document}</strong><br/>"
            f"<em>{self.location_label}</em><br/>"
            f"<strong>Moment :</strong> {self.moment_text()}<br/>"
            f"<strong>Personnes :</strong> {self.individuals_text()}<br/>"
            f"<strong>Résumé :</strong> {self.summary or '—'}"
            "</div>"
        )


class _Geocoder:
    """Simple wrapper around ``geopy`` with local caching."""

    def __init__(self) -> None:
        self._geolocator = Nominatim(user_agent="vidocq_app")
        self._rate_limited = RateLimiter(
            self._geolocator.geocode, min_delay_seconds=1, swallow_exceptions=True
        )
        self._cache: Dict[str, Optional[Tuple[float, float]]] = self._load_cache()

    def _load_cache(self) -> Dict[str, Optional[Tuple[float, float]]]:
        if _GEOCODE_CACHE_PATH.exists():
            with open(_GEOCODE_CACHE_PATH, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            return {
                key: tuple(value) if value is not None else None
                for key, value in payload.items()
            }
        return {}

    def _save_cache(self) -> None:
        serialisable = {
            key: list(value) if value is not None else None
            for key, value in self._cache.items()
        }
        with open(_GEOCODE_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(serialisable, fh, ensure_ascii=False, indent=2)

    def geocode(self, label: str) -> Optional[Tuple[float, float]]:
        normalised = label.strip().lower()
        if not normalised:
            return None

        if normalised in self._cache:
            return self._cache[normalised]

        location = self._rate_limited(label)
        if location:
            coordinates: Optional[Tuple[float, float]] = (
                float(location.latitude),
                float(location.longitude),
            )
        else:
            coordinates = None

        self._cache[normalised] = coordinates
        self._save_cache()
        return coordinates


_GEOCODER: Optional[_Geocoder] = None


def _get_geocoder() -> _Geocoder:
    global _GEOCODER
    if _GEOCODER is None:
        _GEOCODER = _Geocoder()
    return _GEOCODER


def _call_ollama(prompt: str) -> Optional[str]:
    payload = {"model": _LLM_MODEL, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _LLM_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None

    content = payload.get("response")
    if isinstance(content, str):
        content = content.strip()
        return content or None
    return None


def _extract_json_object(raw: str) -> Optional[Dict[str, object]]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _normalise_people(value: object) -> List[str]:
    if isinstance(value, str):
        tokens = re.split(r"[,;/\n]", value)
        return [token.strip() for token in tokens if token.strip()]

    if isinstance(value, Iterable):
        cleaned: List[str] = []
        for item in value:
            if isinstance(item, str):
                token = item.strip()
            else:
                token = str(item).strip()
            if token:
                cleaned.append(token)
        return cleaned

    return []


def _combine_moment_parts(dates: Sequence[str], times: Sequence[str]) -> str:
    parts: List[str] = []

    unique_dates = []
    seen_dates = set()
    for date in dates:
        value = str(date).strip()
        if value and value not in seen_dates:
            seen_dates.add(value)
            unique_dates.append(value)
    if unique_dates:
        parts.append(", ".join(sorted(unique_dates)))

    unique_times: List[str] = []
    for time in times:
        value = str(time).strip()
        if value and value not in unique_times:
            unique_times.append(value)
    if unique_times:
        parts.append(", ".join(unique_times))

    return " – ".join(parts)


def _llm_details_for_location(
    document_id: str,
    location_label: str,
    context: str,
) -> Optional[Tuple[str, List[str], str]]:
    trimmed = context.strip()
    if not trimmed:
        return None

    cache_key = (document_id, location_label.strip().lower())
    cached = _LLM_DETAILS_CACHE.get(cache_key)
    if cached is not None:
        summary, people, moment = cached
        return summary, list(people), moment

    if len(trimmed) > _MAX_CONTEXT_CHARS:
        trimmed = trimmed[:_MAX_CONTEXT_CHARS]

    prompt = textwrap.dedent(
        f'''
Tu es un analyste francophone chargé de décrire un événement.

À partir du passage ci-dessous, extrait uniquement les informations liées à l'événement se déroulant au lieu « {location_label} ».

Réponds en fournissant strictement un objet JSON respectant le format suivant :
{{
  "resume": "résumé concis en une ou deux phrases",
  "personnes": ["Nom Prénom", ...],
  "moment": "description brève du moment (date, heure, période…)"
}}

- "personnes" doit contenir une liste de personnes impliquées (vide si aucune n'est mentionnée).
- "moment" doit préciser la date, l'heure ou la période associée à cet événement, si l'information existe.
- N'ajoute aucun autre texte en dehors de l'objet JSON.

Passage à analyser :
"""{trimmed}"""
'''
    ).strip()

    raw = _call_ollama(prompt)
    if not raw:
        return None

    payload = _extract_json_object(raw)
    if not payload:
        return None

    summary = str(
        payload.get("resume")
        or payload.get("résumé")
        or payload.get("summary")
        or ""
    ).strip()

    individuals = _normalise_people(
        payload.get("personnes")
        or payload.get("personnalites")
        or payload.get("individus")
        or payload.get("people")
        or []
    )

    moment = str(
        payload.get("moment")
        or payload.get("date")
        or payload.get("horaires")
        or payload.get("when")
        or ""
    ).strip()

    _LLM_DETAILS_CACHE[cache_key] = (summary, tuple(individuals), moment)

    return summary, individuals, moment


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_T = TypeVar("_T")


def _unique_preserve_order(values: Sequence[_T]) -> List[_T]:
    seen = set()
    ordered: List[_T] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _split_sentences(text: str) -> List[str]:
    parts = [segment.strip() for segment in _SENTENCE_SPLIT_RE.split(text) if segment.strip()]
    if not parts:
        text = text.strip()
        return [text] if text else []
    return parts


def _context_for_location(sentences: Sequence[str], location_label: str) -> str:
    normalised = location_label.casefold()
    context_sentences: List[str] = []
    for index, sentence in enumerate(sentences):
        if normalised in sentence.casefold():
            start = max(0, index - 1)
            stop = min(len(sentences), index + 2)
            for neighbour in sentences[start:stop]:
                if neighbour not in context_sentences:
                    context_sentences.append(neighbour)
    return " ".join(context_sentences).strip()


def _details_for_location(
    document_id: str,
    record: Dict[str, Iterable[str]],
    sentences: Sequence[str],
    location_label: str,
) -> Tuple[str, List[str], str]:
    context = _context_for_location(sentences, location_label)

    fallback_summary = str(record.get("summary") or "").strip()
    fallback_individuals = [
        str(value).strip() for value in record.get("individuals", []) if str(value).strip()
    ]
    fallback_dates = [str(value).strip() for value in record.get("dates", []) if str(value).strip()]
    fallback_times = [str(value).strip() for value in record.get("times", []) if str(value).strip()]
    fallback_moment = _combine_moment_parts(fallback_dates, fallback_times)

    summary = fallback_summary
    individuals = list(fallback_individuals)
    moment = fallback_moment

    if context:
        llm_details = _llm_details_for_location(document_id, location_label, context)
        if llm_details:
            llm_summary, llm_people, llm_moment = llm_details
            if llm_summary:
                summary = llm_summary
            if llm_people:
                individuals = llm_people
            if llm_moment:
                moment = llm_moment

        if not summary:
            summary = extract_events(context, nb_sentences=2).strip() or context
        if not individuals:
            individuals = _unique_preserve_order(extract_individuals(context))
        if not moment:
            dates = sorted(set(extract_dates(context)))
            times = _unique_preserve_order(extract_times(context))
            moment = _combine_moment_parts(dates, times)

    if not summary:
        summary = fallback_summary
    if not individuals:
        individuals = fallback_individuals
    if not moment:
        moment = fallback_moment

    return summary, individuals, moment


def build_event_markers(
    document_id: str,
    record: Dict[str, Iterable[str]],
    document_text: str,
    *,
    prefer_addresses: bool = True,
    max_locations: int = 10,
) -> List[EventMarker]:
    """Create :class:`EventMarker` instances from an entity payload."""

    addresses = [item for item in record.get("addresses", []) if item]
    raw_locations = [item for item in record.get("locations", []) if item]

    if prefer_addresses and addresses:
        candidates = addresses + [loc for loc in raw_locations if loc not in addresses]
    else:
        candidates = addresses + [loc for loc in raw_locations if loc not in addresses]

    seen_labels = set()
    markers: List[EventMarker] = []
    geocoder = _get_geocoder()
    sentences = _split_sentences(document_text)

    for label in candidates:
        key = label.strip()
        if not key:
            continue
        normalised = key.lower()
        if normalised in seen_labels:
            continue

        coords = geocoder.geocode(key)
        seen_labels.add(normalised)

        if coords is None:
            continue

        summary, individuals, moment = _details_for_location(
            document_id, record, sentences, key
        )

        markers.append(
            EventMarker(
                document=document_id,
                location_label=key,
                latitude=coords[0],
                longitude=coords[1],
                summary=summary,
                individuals=individuals,
                moment=moment,
            )
        )

        if len(markers) >= max_locations:
            break

    return markers


def _initial_view(markers: Sequence[EventMarker]) -> Tuple[float, float]:
    latitudes = [marker.latitude for marker in markers]
    longitudes = [marker.longitude for marker in markers]
    return (sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes))


def render_event_map(markers: Sequence[EventMarker]) -> Optional[str]:
    """Return an HTML representation of the map for the given markers."""

    if not markers:
        return None

    initial_lat, initial_lon = _initial_view(markers)
    fmap = folium.Map(location=[initial_lat, initial_lon], zoom_start=6, tiles="OpenStreetMap")

    for marker in markers:
        folium.Marker(
            location=[marker.latitude, marker.longitude],
            popup=folium.Popup(marker.popup_html(), max_width=300),
            tooltip=folium.Tooltip(marker.tooltip_html(), sticky=True, parse_html=True),
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(fmap)

    return fmap.get_root().render()


def markers_to_rows(markers: Sequence[EventMarker]) -> List[Dict[str, str]]:
    """Transform a list of markers into serialisable rows."""

    rows: List[Dict[str, str]] = []
    for marker in markers:
        rows.append(
            {
                "document": marker.document,
                "lieu": marker.location_label,
                "latitude": f"{marker.latitude:.6f}",
                "longitude": f"{marker.longitude:.6f}",
                "personnes": marker.individuals_text(),
                "moment": marker.moment_text(),
                "résumé": marker.summary or "—",
            }
        )
    return rows


__all__ = [
    "EventMarker",
    "build_event_markers",
    "markers_to_rows",
    "render_event_map",
]
