# -*- coding: utf-8 -*-

############################
# Word cloud builder       #
#                          #
# Last update : 2025/08/11 #
############################


# On utilise le client OpenAI pointé vers Groq (base_url="https://api.groq.com/openai/v1"), avec la clé dans GROQ_API_KEY.

# Objectif : réduire le nombre d’appels réseau en envoyant plusieurs blocs de texte en une seule requête (batch).

# Pipeline complète : découpe du fichier → batching → appel modèle → checkpoint → export CSV/JSON.




# Fichier texte complet
#        │
#        ▼
# decouper_texte()
#        │
#        ▼
# Liste de blocs
# [ bloc0, bloc1, bloc2, bloc3, bloc4, ... ]
#        │
#        ▼
# extraire_faits_depuis_texte_long_batch()
#        │
#        ├── Batch 1 : bloc0 à bloc7
#        ├── Batch 2 : bloc8 à bloc15
#        └── Batch 3 : bloc16 à bloc...

import pandas as pd
from openai import OpenAI
import time
import json
import os
import re
import math
from typing import Dict, List, Any
from groq import Groq


# --- 1. Configuration du client ---

# 🔑 clé Groq
#  Bonne pratique : lire la clé depuis un fichier texte
with open("groq_key.txt", "r", encoding="utf-8") as f:
    GROQ_API_KEY = f.read().strip()

# 📍 Configuration du client OpenAI pour l'API Groq
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    default_headers={"User-Agent": "pipeline-faits/1.0"})


# --- 2. Fonction de découpage d'un texte ---

def decouper_texte(nom_fichier, target_chars=2000, overlap=200, min_chars=400):
    with open(nom_fichier, "r", encoding="utf-8") as f:
        texte = f.read()
    morceaux, i, n = [], 0, len(texte)
    while i < n:
        j = min(i + target_chars, n)
        chunk = texte[i:j]
        if j < n:
            fin = max(chunk.rfind(". "), chunk.rfind("? "), chunk.rfind("! "))
            if fin > min_chars:
                chunk = chunk[:fin+1]
                j = i + len(chunk)
        if len(chunk) >= min_chars:
            morceaux.append(chunk)
        i = max(j - overlap, j)
    return morceaux


# --- 3. Parse TSV ---

# NOTE : TSV = Tab-Separated Values - format texte pour lequel la séparation se fait avec une tabulation (équivalent de CSV, mais avec TAB au lieu de ; )

# fonction d'extraction de texte entre deux marqueurs
def _extract_between_markers(text: str, start="BEGIN_TSV", end="END_TSV") -> str:

    """
    Recherche dans `text` le premier bloc de texte situé entre les marqueurs
    `start` et `end`, et retourne uniquement ce contenu.

    La recherche est insensible aux retours à la ligne, et tolère des espaces
    autour du contenu extrait. Si aucun bloc n'est trouvé, retourne une chaîne vide.

    Paramètres
    ----------
    text : str
        Chaîne de texte à analyser.
    start : str, optionnel
        Marqueur de début (par défaut "BEGIN_TSV").
    end : str, optionnel
        Marqueur de fin (par défaut "END_TSV").

    Retour
    ------
    str
        Contenu extrait entre `start` et `end`, nettoyé des espaces en tête/fin,
        ou "" si les marqueurs ne sont pas trouvés.
    """
     
    m = re.search(rf"{re.escape(start)}\s*(.*?)\s*{re.escape(end)}", text, flags=re.S)
    return m.group(1).strip() if m else ""

# Exemple
text = "BEGIN_TSV Ceci est un test END_TSV"
_extract_between_markers(text)



# Fonction de construction d'un dictionnaire de clés {resume, lieu, moment, individus} à partir d'un texte avec marqueurs
def _parse_tsv_lines_with_markers(blob: str):
    """
    Récupère le bloc entre BEGIN_TSV / END_TSV,
    puis parse des lignes TSV → 4 colonnes: resume, lieu, moment, individus.
    Ignore les lignes qui n'ont pas 4 colonnes.
    """
    inner = _extract_between_markers(blob, "BEGIN_TSV", "END_TSV")
    if not inner:
        return []

    rows = []
    for raw in inner.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        parts = parts[:4]
        rows.append({
            "resume":    re.sub(r"\s+", " ", parts[0].strip()),
            "lieu":      re.sub(r"\s+", " ", parts[1].strip()),
            "moment":    re.sub(r"\s+", " ", parts[2].strip()),
            "individus": re.sub(r"\s+", " ", parts[3].strip()),
        })
    return rows

# 1. récupérer le texte interne entre BEGIN_TSV et END_TSV
# 2. interpréter ce texte comme un TSV (tab-separated values), une ligne = un enregistrement, 4 colonnes attendues (dans l’ordre) : resume, lieu, moment, individus
# 3. retourner une liste de dictionnaires normalisés

# Exemple
blob = """
Du texte avant
BEGIN_TSV
Vol à l'étalage\tParis 11e\t2024-05-02\t2 suspects
Rencontre amicale\tLyon\tsoirée\tAlice, Bob
Ligne incomplète\tToulouse
END_TSV
Du texte après
"""
_parse_tsv_lines_with_markers(blob)

# NOTE : la ligne incomplète est ignorée car elle a moins de 4 colonnes



# --- 4. Prompt ---

# prompt sur les règles que doit appliquer le LLM
rules_param = (
    "RENVOIE UNIQUEMENT un bloc entre ces marqueurs, sans rien d'autre :\n"
    "BEGIN_TSV\n"
    "(lignes TSV)\n"
    "END_TSV\n"
    "\n"
    "Format : lignes TSV, une ligne par fait, EXACTEMENT 4 colonnes dans cet ordre :\n"
    "resume\tlieu\tmoment\tindividus\n"
    "\n"
    "DÉFINITIONS :\n"
    "- resume : résumé très bref (5 à 12 mots), décrivant l’action principale. "
    "  La colonne resume ne mentionne aucun lieu, aucun moment, aucun individu.\n"
    "- lieu : lieu où l'action s'est déroulée (adresse, nom de lieu, ville) ; sinon vide.\n"
    "- moment : utiliser le schéma 'DATE - HEURE' si dispo. "
    "  • Si seule la date est connue : 'DATE - '\n"
    "  • Si seule l'heure est connue : ' - HEURE'\n"
    "  • Si un moment textuel existe ('le matin', 'au crépuscule', 'hier soir', 'pendant la cérémonie'), "
    "    l’insérer dans la partie manquante (ex. ' - le matin', '05 mai 2025 - le soir'). "
    "  • Si aucun repère temporel : moment vide.\n"
    "- individus : personnes impliquées, séparées par '; ' (noms complets si connus ; sinon 'homme inconnu', etc.) ; peut être vide.\n"
    "\n"
    "CONTRAINTES :\n"
    "- Extraire TOUS les faits distincts, même mineurs ; une ligne par fait ; ne pas fusionner.\n"
    "- Ne pas mélanger les informations entre colonnes.\n"
    "- Toujours produire 4 colonnes séparées par TAB ; colonnes vides autorisées.\n"
    "- INTERDIT : virgules pour séparer les colonnes, guillemets, Markdown, texte hors des marqueurs.\n"
    "- Remplacer toute tabulation/retour de ligne interne à une cellule par un espace.\n"
    "\n"
    "EXEMPLES :\n"
    "BEGIN_TSV\n"
    "Échange devant café Le Nautilus\t25 rue de Crimée 75019 Paris\t02 mai 2025 - 08h47\tClaire Dubois; Julien Morel\n"
    "Visite chez Claire\t18 rue de Charonne 75011 Paris\t04 mai 2025 - 15h15\tClaire Dubois; Fatima El-Haddad\n"
    "Discussion près de la gare\tGare de Lyon 75012 Paris\t - en fin d’après-midi\tThomas Rivière\n"
    "Départ précipité\t\t10 mai 2025 - 23h48\tFatima El-Haddad\n"
    "Observation discrète\t\t - \t\n"
    "END_TSV\n"
)



# 5. --- Modèles à essayer ---

# Modèles à essayer (en priorité)
MODEL_CANDIDATES = [
    "llama-3.1-8b-instant",     # 500K TPD
    "llama-3.3-70b-versatile",  # qualité
]


# 6. --- Envoi d'un prompt au LLM ---         

# fonction d'envoi d'un prompt construit dynamiquement à un LLM
def _llm_extract_tsv(items, model, max_tokens=1200, temperature=0.1):

    """
    Envoie un prompt au LLM pour extraire des faits d'un texte et les formater
    sous forme de lignes TSV (4 colonnes : resume, lieu, moment, individus).

    Le prompt inclut les règles de formatage définies dans `rules_param`
    ainsi que les textes à analyser, fournis dans `items`.
    La fonction retourne le texte brut généré par le LLM.

    Paramètres
    ----------
    items : list[dict]
        Liste de dictionnaires contenant au minimum :
        - "id" : identifiant unique de l'élément
        - "texte" : texte brut à analyser.
    model : str
        Nom du modèle de langage à utiliser (ex. "gpt-4o", "gpt-3.5-turbo").
    max_tokens : int, optionnel
        Nombre maximum de tokens que le LLM peut générer (par défaut 1200).
    temperature : float, optionnel
        Température du LLM (contrôle la créativité ; 0.1 = sortie très déterministe).

    Retour
    ------
    str
        Texte brut renvoyé par le LLM, censé contenir uniquement
        un bloc `BEGIN_TSV ... END_TSV` formaté selon `rules_param`.
        Chaîne vide si aucune réponse n’est reçue.

    Exemple
    -------
    >>> items = [{"id": 1, "texte": "Accident rue Victor Hugo à 14h."}]
    >>> print(_llm_extract_tsv(items, model="gpt-4o"))
    BEGIN_TSV
    Accident sur voie publique	rue Victor Hugo 75000 Paris	 - 14h00	
    END_TSV
    """
        
    messages = [
        {"role": "system", "content": "Tu es un extracteur d'événements, exhaustif et strict sur le format."},
        {"role": "user", "content": rules_param + "\n\nTEXTE À ANALYSER (génère une ou plusieurs lignes par fait détecté) :\n"
                          + json.dumps({"items":[{"id":it["id"],"texte":it["texte"]} for it in items]}, ensure_ascii=False)}
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content if resp.choices else ""


# 7. --- Extraction structurée ---

# fonction d'extraction structurée : le chef d'orchestre de ce fichier 
def extraction_structuree(
    nom_fichier: str,
    batch_size: int = 2,
    model: str = "llama-3.1-8b-instant",
    target_chars: int = 2000,
    overlap: int = 200,
    min_chars: int = 400,
    out_tsv: str = "faits_extraits.tsv",
    checkpoint_tsv: str = "checkpoint_faits.tsv",
    max_completion_tokens: int = 1200,
    temperature: float = 0.1,
    qps: float = 0.4,           # ≈ 24 RPM
    keep_checkpoint: bool = False,
):
    """
    Lit un fichier texte brut, le découpe en blocs, envoie ces blocs à un modèle
    de langage pour en extraire des faits structurés au format TSV (4 colonnes),
    et enregistre le résultat final dans un fichier TSV.

    Les extractions sont effectuées par batchs de blocs. Un fichier checkpoint
    est maintenu pour enregistrer les résultats intermédiaires et permettre
    de reprendre le traitement en cas d'interruption.

    Paramètres
    ----------
    nom_fichier : str
        Chemin du fichier texte (.txt) à analyser.
    batch_size : int, optionnel
        Nombre de blocs à traiter par appel au LLM (par défaut 2).
    model : str, optionnel
        Nom du modèle principal à utiliser (par défaut "llama-3.1-8b-instant").
    target_chars : int, optionnel
        Nombre cible de caractères par bloc avant envoi au LLM.
    overlap : int, optionnel
        Nombre de caractères qui se chevauchent entre deux blocs consécutifs.
    min_chars : int, optionnel
        Taille minimale d’un bloc (en caractères).
    out_tsv : str, optionnel
        Nom du fichier TSV final contenant tous les faits extraits.
    checkpoint_tsv : str, optionnel
        Nom du fichier TSV de checkpoint (résultats intermédiaires).
    max_completion_tokens : int, optionnel
        Nombre maximum de tokens générés par le LLM par appel.
    temperature : float, optionnel
        Température de génération du LLM (0.1 = très déterministe).
    qps : float, optionnel
        Limite approximative en requêtes par seconde (par défaut 0.4 ≈ 24 RPM).
    keep_checkpoint : bool, optionnel
        Si False, supprime le fichier de checkpoint existant avant de commencer.

    Retour
    ------
    pandas.DataFrame
        DataFrame contenant les faits extraits avec colonnes :
        ["resume", "lieu", "moment", "individus"].

    Effets de bord
    --------------
    - Écrit un fichier TSV final (`out_csv`) avec les faits extraits.
    - Écrit un fichier checkpoint (`checkpoint_tsv`) au fur et à mesure.
    - Sauvegarde des fichiers de debug pour chaque batch.

    Notes
    -----
    - Si un batch complet renvoie une réponse vide ou incomplète, la fonction
      repasse en mode "singleton" (un bloc par appel) pour ce batch.
    - Les faits extraits respectent le format et les règles définis dans `rules_param`.
    - Le découpage du texte est effectué par la fonction `decouper_texte`.
    """
    blocs = decouper_texte(nom_fichier, target_chars, overlap, min_chars)
    print(f"✅ {len(blocs)} blocs détectés.")
    if not blocs:
        df0 = pd.DataFrame(columns=["resume","lieu","moment","individus"])
        df0.to_csv(out_tsv, index=False, encoding="utf-8", sep="\t")
        print(f"💾 {out_tsv} écrit (0 lignes).")
        return df0

    # checkpoint
    if not keep_checkpoint and os.path.exists(checkpoint_tsv):
        try:
            os.remove(checkpoint_tsv)
        except Exception:
            pass

    header_written = False
    def write_checkpoint(rows):
        nonlocal header_written
        if not rows:
            return
        df_ck = pd.DataFrame(rows, columns=["resume","lieu","moment","individus"])
        df_ck.to_csv(
            checkpoint_tsv,
            mode="a",
            index=False,
            header=(not header_written and (not os.path.exists(checkpoint_tsv))),
            encoding="utf-8",
            sep="\t",
        )
        header_written = True

    lignes = []
    last_call = 0.0

    # boucle batchs
    for start in range(0, len(blocs), batch_size):
        end = min(start + batch_size, len(blocs))
        batch_items = [{"id": i, "texte": blocs[i].strip()} for i in range(start, end)]

        # QPS simple
        now = time.time()
        delta = 1.0 / qps - (now - last_call)
        if delta > 0:
            time.sleep(delta)
        last_call = time.time()

        # Appel principal (on essaie d'abord 'model', sinon autres candidats)
        text_out = ""
        last_err = None
        for m in [model] + [mm for mm in MODEL_CANDIDATES if mm != model]:
            try:
                text_out = _llm_extract_tsv(batch_items, m, max_tokens=max_completion_tokens, temperature=temperature)
                _save_debug(text_out, f"batch_{start+1}_{end}")
                if text_out:
                    break
            except Exception as e:
                last_err = e
                continue

        if not text_out and last_err:
            print(f"⚠️ Erreur batch {start+1}-{end}: {last_err}")

        # Parse TSV
        new_rows = _parse_tsv_lines_with_markers(text_out)

        # Plan B : si le batch renvoie peu/néant, on traite item par item
        if (not new_rows) and len(batch_items) > 1:
            print("🧩 Réponse vide/insuffisante sur le batch ⇒ bascule en singletons.")
            for it in batch_items:
                try:
                    one = _llm_extract_tsv([it], model, max_tokens=min(1400, max_completion_tokens+200), temperature=temperature)
                    _save_debug(one, f"item_{it['id']}")
                except Exception as e:
                    print(f"❌ Item {it['id']} en échec: {str(e)[:120]}")
                    one = ""
                new_rows.extend(_parse_tsv_lines_with_markers(one))

        # Accumule + checkpoint
        before = len(lignes)
        lignes.extend(new_rows)
        write_checkpoint(lignes[before:])

        # Progress
        pct = 100.0 * end / len(blocs)
        print(f"Batch {start+1}-{end} traité | {end}/{len(blocs)} blocs ({pct:.1f}%) – {len(new_rows)} faits")

    # Export final
    df = pd.DataFrame(lignes, columns=["resume","lieu","moment","individus"])
    df.to_csv(out_tsv, index=False, encoding="utf-8", sep="\t")
    print(f"💾 {out_tsv} écrit ({len(df)} lignes).")
    return df



# 8. --- Application ---

# on applique la fonction extraction_structuree() à un compte-rendu d'enquête simulé
# import os

# try:
#     base_dir = os.path.dirname(__file__)
# except NameError:
#     # Fallback si __file__ n'est pas défini
#     base_dir = os.getcwd()

# nom_fichier = os.path.join(base_dir, "data", "CRE_simulations", "CRE.txt")
# df = extraction_structuree(nom_fichier=nom_fichier)
# df




