
# -*- coding: utf-8 -*-

############################
# Mapping chrono           #
#                          #
# Last update : 2025/08/12 #
############################

# But : construire une carte chronologique

# Principe :

# - prendre le DataFrame (colonnes resume, lieu, moment, individus) +
#   la fonction geocoder_lieu(lieu) et produire une carte Folium qui :

#       - place des points numérotés dans l’ordre chronologique
#       - trace une polyline entre les points
#       - ajoute des flèches le long de la ligne
#       - ouvre un popup complet au clic (Événement / Lieu / Moment / Individus)


# mapping_chrono.py
from __future__ import annotations
import folium
from folium import Map, CircleMarker, Popup, Marker
from typing import List, Dict, Tuple, Optional
from time_utils import parse_moment_fr

# ---------- Helpers visuels ----------

def _add_badge_label(map_obj: Map, lat: float, lon: float, text: str,
                     dx: int = 12, dy: int = -12,
                     bg: str = "white", fg: str = "#333", border: str = "#333"):
    """
    Ajoute un petit badge (DivIcon) décalé par rapport au point (dx, dy en px).
    dx>0 => à droite ; dy<0 => au-dessus. Le badge n'intercepte pas le clic.
    """
    html = f"""
    <div style="
        transform: translate({dx}px, {dy}px);
        background:{bg}; color:{fg}; border:1px solid {border};
        border-radius:10px; padding:1px 6px; font-size:11px; font-weight:700;
        pointer-events:none; white-space:nowrap;">
        {text}
    </div>
    """
    Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=html, icon_size=(0,0), icon_anchor=(0,0))
    ).add_to(map_obj)


def _split_individus(s: str) -> List[str]:
    if not s:
        return []
    # individus séparés par ';'
    return [x.strip() for x in str(s).split(";") if x.strip()]


# ---------- Préparation des événements ----------

def preprocess_events_global(df) -> List[Dict]:
    """
    Transforme le df en une liste d'événements triés par moment (datetime),
    sans géocodage (il sera fait côté app via geocoder_lieu).
    Chaque item: {resume, lieu, moment(str), individus(str), t(datetime|None)}
    """
    events = []
    for _, row in df.iterrows():
        resume    = str(row.get("resume", "")).strip()
        lieu      = str(row.get("lieu", "")).strip()
        moment    = str(row.get("moment", "")).strip()
        individus = str(row.get("individus", "")).strip()
        t = parse_moment_fr(moment)
        events.append({"resume": resume, "lieu": lieu, "moment": moment, "individus": individus, "t": t})
    # Trier: datés d'abord, puis non datés
    events.sort(key=lambda e: (e["t"] is None, e["t"]))
    return events


def preprocess_events_by_individual(df, person: str) -> List[Dict]:
    """
    Filtre les événements pour 'person' (présente dans la colonne individus),
    puis trie par moment. Si aucun, retourne [].
    """
    if not person:
        return []
    kept = []
    for _, row in df.iterrows():
        noms = _split_individus(row.get("individus", ""))
        if person in noms:
            resume = str(row.get("resume", "")).strip()
            lieu   = str(row.get("lieu", "")).strip()
            moment = str(row.get("moment", "")).strip()
            t = parse_moment_fr(moment)
            kept.append({"resume": resume, "lieu": lieu, "moment": moment, "individus": person, "t": t})
    kept.sort(key=lambda e: (e["t"] is None, e["t"]))
    return kept


# ---------- Cartes (statique / dynamique) ----------

def build_map_static(events: List[Dict], geocoder_lieu,
                     point_color: str = "red",
                     label_dx: int = 12, label_dy: int = -12) -> Optional[Map]:
    """
    Affiche TOUS les points (statique). Numérotation 1..N à côté des points.
    events: liste déjà triée (globale OU filtrée par individu).
    """
    # Géocodage
    pts: List[Tuple[float, float, Dict]] = []
    for ev in events:
        lieu = ev.get("lieu", "").strip()
        if not lieu:
            continue
        geo = geocoder_lieu(lieu)
        if not geo:
            continue
        lat, lon, _src = geo
        pts.append((lat, lon, ev))

    if not pts:
        return None

    # Carte centrée sur le 1er point
    m = Map(location=[pts[0][0], pts[0][1]], zoom_start=12, tiles="OpenStreetMap")

    # Tous les points + badges
    for i, (lat, lon, ev) in enumerate(pts, start=1):
        html = (
            f"<b>#{i:02d}</b><br>"
            f"<b>Événement</b> : {ev['resume']}<br>"
            f"<b>Lieu</b> : {ev['lieu']}<br>"
            f"<b>Moment</b> : {ev['moment']}<br>"
            f"<b>Individus</b> : {ev.get('individus','')}"
        )
        CircleMarker(
            location=[lat, lon],
            radius=6, color=point_color, fill=True, fill_color=point_color, fill_opacity=0.9,
            popup=Popup(html, max_width=350),
        ).add_to(m)
        _add_badge_label(m, lat, lon, f"{i}", dx=label_dx, dy=label_dy, bg="white", fg=point_color, border=point_color)

    # ✅ Adapter la vue pour englober tous les points (si au moins 2)
    if len(pts) >= 2:
        m.fit_bounds([[lat, lon] for (lat, lon, _) in pts])

    return m

# mapping_chrono.py

def build_map_dynamic(
    events: list[dict],
    geocoder_lieu,
    idx: int,
    point_color: str = "red",
    label_dx: int = 12,
    label_dy: int = -12,
    fixed_center: tuple[float, float] | None = None,
    fixed_zoom: int | None = None,
):
    """
    Affiche UNIQUEMENT le point courant (dynamique).
    - Si fixed_center/fixed_zoom sont fournis, la carte garde cette vue et ne "saute" plus.
    """
    N = len(events)
    if N == 0 or idx < 0 or idx >= N:
        return None, N

    ev = events[idx]
    lieu = ev.get("lieu", "").strip()
    if not lieu:
        return None, N

    geo = geocoder_lieu(lieu)
    if not geo:
        return None, N
    lat, lon, _src = geo

    # ✅ keep map steady if fixed_center/zoom provided
    center = list(fixed_center) if fixed_center else [lat, lon]
    zoom   = fixed_zoom if fixed_zoom is not None else 13

    m = Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    html = (
        f"<b>#{idx+1:02d}</b><br>"
        f"<b>Événement</b> : {ev['resume']}<br>"
        f"<b>Lieu</b> : {ev['lieu']}<br>"
        f"<b>Moment</b> : {ev['moment']}<br>"
        f"<b>Individus</b> : {ev.get('individus','')}"
    )
    CircleMarker(
        location=[lat, lon],
        radius=8, color=point_color, fill=True, fill_color=point_color, fill_opacity=0.95,
        popup=Popup(html, max_width=350),
    ).add_to(m)
    _add_badge_label(m, lat, lon, f"{idx+1}", dx=label_dx, dy=label_dy, bg="white", fg=point_color, border=point_color)

    return m, N

