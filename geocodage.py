# -*- coding: utf-8 -*-

############################
# Geocodage                #
#                          #
# Last update : 2025/08/11 #
############################


import re
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import streamlit as st

# Liste simplifiée des types de voie
_TYPES_VOIE = [
    "rue", "avenue", "av.", "boulevard", "bd", "chemin",
    "impasse", "quai", "route", "allée", "allee", "square",
    "place", "cours", "passage"
]

def _est_adresse_complete(lieu: str) -> bool:
    """Détermine si le texte ressemble à une adresse complète (numéro + type de voie)."""
    if not lieu:
        return False
    txt = lieu.lower()
    a_un_numero = any(ch.isdigit() for ch in txt)
    a_type_voie = any(t in txt for t in _TYPES_VOIE)
    return a_un_numero and a_type_voie

# Instanciation du geocoder Nominatim
_geolocator = Nominatim(user_agent="vidocq_app/1.0", timeout=10)
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1.0)

@st.cache_data(show_spinner=False)
def geocoder_lieu(lieu: str, country_hint: str = "France"):
    """
    Géocode un lieu en retournant (lat, lon, source) ou None.
    source ∈ {'adresse','ville'}.
    """
    if not lieu or not lieu.strip():
        return None
    q = lieu.strip()
    try:
        if _est_adresse_complete(q):
            loc = _geocode(f"{q}, {country_hint}")
            if loc:
                return (loc.latitude, loc.longitude, "adresse")
        # Ville/village → mairie si possible
        loc = _geocode(f"Mairie {q}, {country_hint}")
        if not loc:
            loc = _geocode(f"{q}, {country_hint}")
        if loc:
            return (loc.latitude, loc.longitude, "ville")
    except Exception:
        return None
    return None
