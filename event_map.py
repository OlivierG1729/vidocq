"""Utilities to convert extracted entities into an interactive map of events.

This module centralises the logic that geocodes textual locations and builds a
Folium map that can be embedded inside the Streamlit application.  The goal is
that the Streamlit layer only has to provide the raw entity payloads coming
from :mod:`entity_extractor` and receive an HTML fragment representing the map.
"""

from __future__ import annotations

import json
import re
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


@dataclass
class EventMarker:
    """Representation of a location associated to an event in a document."""

    document: str
    location_label: str
    latitude: float
    longitude: float
    summary: str
    individuals: Sequence[str]
    dates: Sequence[str]
    times: Sequence[str]

    def _join(self, values: Sequence[str]) -> str:
        cleaned = [value.strip() for value in values if value and value.strip()]
        return ", ".join(cleaned) if cleaned else "—"

    def individuals_text(self) -> str:
        """Return a human readable list of individuals."""

        return self._join(self.individuals)

    def dates_text(self) -> str:
        """Return a human readable list of dates."""

        return self._join(self.dates)

    def times_text(self) -> str:
        """Return a human readable list of times."""

        return self._join(self.times)

    def moment_text(self) -> str:
        """Combine dates and times to describe when the event happened."""

        parts = []
        dates = self.dates_text()
        times = self.times_text()
        if dates != "—":
            parts.append(dates)
        if times != "—":
            parts.append(times)
        return " – ".join(parts) if parts else "—"

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
    record: Dict[str, Iterable[str]],
    sentences: Sequence[str],
    location_label: str,
) -> Tuple[str, List[str], List[str], List[str]]:
    context = _context_for_location(sentences, location_label)
    if context:
        summary = extract_events(context, nb_sentences=2).strip()
        if not summary:
            summary = context
        individuals = _unique_preserve_order(extract_individuals(context))
        dates = sorted(set(extract_dates(context)))
        times = _unique_preserve_order(extract_times(context))
    else:
        summary = str(record.get("summary") or "")
        individuals = list(record.get("individuals", []))
        dates = list(record.get("dates", []))
        times = list(record.get("times", []))

    return summary, individuals, dates, times


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

        summary, individuals, dates, times = _details_for_location(record, sentences, key)

        markers.append(
            EventMarker(
                document=document_id,
                location_label=key,
                latitude=coords[0],
                longitude=coords[1],
                summary=summary,
                individuals=individuals,
                dates=dates,
                times=times,
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
                "personnes": ", ".join(marker.individuals) or "—",
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
