
# -*- coding: utf-8 -*-

############################
# Time utils               #
#                          #
# Last update : 2025/08/12 #
############################


# But : parser les champs "moment" et les convertir en objet datetime

# NOTE : 
# Parser = lire du texte brut et le transformer en données structurées
#  (objets, variables, etc.) qu’on peut manipuler dans le code.

import re, pandas as pd
from datetime import datetime, time

_HEURES_TEXTUELLES = {
    "matin": time(9, 0), "après-midi": time(15, 0), "apres-midi": time(15, 0),
    "fin d’après-midi": time(17, 30), "fin d'apres-midi": time(17, 30),
    "midi": time(12, 0), "soir": time(20, 0),
    "nuit": time(23, 0), "crépuscule": time(21, 0), "aube": time(6, 0),
}

def _parse_heure_fr(s: str):
    m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{0,2})", s or "")
    if not m: return None
    hh, mm = int(m.group(1)), int(m.group(2) or 0)
    return time(hh, mm) if 0 <= hh < 24 and 0 <= mm < 60 else None

def _heuristique_heure_textuelle(s: str):
    s = (s or "").lower()
    for k, t in _HEURES_TEXTUELLES.items():
        if k in s:
            return t
    return None

def parse_moment_fr(m: str):
    if not m or not str(m).strip():
        return None
    s = str(m).strip()
    parts = [p.strip() for p in s.split(" - ", 1)]
    date_part = parts[0] if parts else ""
    time_part = parts[1] if len(parts) > 1 else ""
    date_dt = pd.to_datetime(date_part, dayfirst=True, errors="coerce") if date_part else pd.NaT
    t = _parse_heure_fr(time_part) or _heuristique_heure_textuelle(time_part)
    if pd.isna(date_dt) and not t:
        return None
    if pd.isna(date_dt):
        date_dt = pd.Timestamp(1900, 1, 1)
    if not t:
        t = time(0, 0)
    return datetime.combine(date_dt.date(), t)
