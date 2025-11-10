# -*- coding: utf-8 -*-
"""
Module : extraction_procedure
Dernière mise à jour : 2025-11-10

But :
  Conversion et extraction structurée de procédures policières (.doc, .docx, .odt, .txt)
  vers un format JSON homogène, via un LLM (Groq).
"""

import os
import re
import json
import subprocess
from typing import Optional

# Conversion de fichiers
import pypandoc
from docx import Document

# --- Configuration du client LLM (Groq) ---
from openai import OpenAI

# 🔑 Lecture de la clé Groq (même que dans extraction_structuree.py)
with open("groq_key.txt", "r", encoding="utf-8") as f:
    GROQ_API_KEY = f.read().strip()

# ⚙️ Initialisation du client (API compatible OpenAI)
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    default_headers={"User-Agent": "vidocq-procedure/1.0"}
)

# Télécharge Pandoc automatiquement s'il n'est pas présent
try:
    pypandoc.get_pandoc_version()
except OSError:
    print("📦 Téléchargement de Pandoc (nécessaire pour les conversions)...")
    pypandoc.download_pandoc()


# ============================================================
# 1️⃣ Conversion universelle vers texte brut
# ============================================================

def convert_to_txt(path: str) -> str:
    """
    Convertit un fichier .doc, .docx, .odt ou .txt en texte brut propre.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext in [".docx", ".doc"]:
        text = convert_doc_to_txt(path)
    elif ext == ".odt":
        text = convert_odt_to_txt(path)
    elif ext == ".txt":
        with open(path, "r", encoding="utf8", errors="ignore") as f:
            text = f.read()
    else:
        raise ValueError(f"Extension non supportée : {ext}")

    # Nettoyage global du texte
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def convert_doc_to_txt(filepath: str) -> str:
    """
    Convertit un fichier .odt / .doc / .docx en .txt utilisable.
    - .odt et .docx : conversion directe via Pandoc
    - .doc : conversion via LibreOffice (soffice.exe)
    """
    base, ext = os.path.splitext(filepath)
    ext = ext.lower()
    txt_path = f"{base}.txt"

    # Assure la présence de pandoc
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        print("📦 Téléchargement automatique de Pandoc...")
        pypandoc.download_pandoc()

    # Cas 1 : DOCX ou ODT → conversion directe via Pandoc
    if ext in [".docx", ".odt"]:
        try:
            pypandoc.convert_file(filepath, "plain", outputfile=txt_path)
            with open(txt_path, "r", encoding="utf8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Erreur conversion {ext.upper()} : {e}")

    # Cas 2 : DOC → conversion intermédiaire via LibreOffice
    elif ext == ".doc":
        try:
            soffice_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            soffice_exe = next((p for p in soffice_paths if os.path.exists(p)), None)
            if soffice_exe is None:
                raise RuntimeError("LibreOffice (soffice.exe) introuvable. Installez-le.")

            docx_path = f"{base}.docx"
            cmd = [
                soffice_exe, "--headless", "--convert-to", "docx",
                "--outdir", os.path.dirname(filepath), filepath
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if not os.path.exists(docx_path):
                raise RuntimeError("Échec conversion DOC → DOCX via LibreOffice.")

            pypandoc.convert_file(docx_path, "plain", outputfile=txt_path)
            with open(txt_path, "r", encoding="utf8", errors="ignore") as f:
                return f.read()

        except Exception as e:
            raise RuntimeError(f"Erreur conversion DOC : {e}")

    elif ext == ".txt":
        with open(filepath, "r", encoding="utf8", errors="ignore") as f:
            return f.read()

    else:
        raise RuntimeError(f"Extension non prise en charge : {ext}")


def convert_odt_to_txt(path: str) -> str:
    """
    Conversion spécifique .odt vers texte brut via pypandoc.
    """
    try:
        text = pypandoc.convert_file(path, "plain", format="odt")
    except Exception as e:
        raise RuntimeError(f"Erreur conversion ODT : {e}")
    text = re.sub(r"\n{2,}", "\n", text.strip())
    return text


# ============================================================
# 2️⃣ Extraction via LLM Groq
# ============================================================

def extract_with_llm(text: str, source_file: Optional[str] = None) -> dict:
    """
    Utilise le LLM Groq pour extraire les informations structurées d'une procédure policière.
    Tente plusieurs modèles en cascade (fallback) pour plus de robustesse.
    """

    MODEL_CANDIDATES = [
        "llama-3.3-70b-versatile",  # modèle principal, précis
        "llama-3.1-8b-instant",     # modèle rapide de secours
    ]

    # --- prompt de base ---
    prompt = f"""
    Voici le texte brut d'une procédure policière française :

    ---
    {text}
    ---

    Analyse ce texte et renvoie un objet JSON complet contenant :
    {{
      "meta": {{
        "source_file": "{os.path.basename(source_file) if source_file else ''}",
        "reference": "(numéro de procédure s’il existe)",
        "commissariat": "(nom du commissariat s’il est mentionné)",
        "qualification_juridique": "(nature de l'infraction)",
        "date_procedure": "(date principale de la procédure)"
      }},
      "personnes": {{
        "mis_en_cause": [{{"nom": "", "prenom": "", "naissance": "", "lieu_naissance": ""}}],
        "victimes": [{{"nom": "", "prenom": ""}}],
        "temoins": [{{"nom": "", "prenom": ""}}],
        "agents": [{{"grade": "", "nom": "", "prenom": ""}}]
      }},
      "faits": {{
        "nature": "",
        "lieu": "",
        "date": "",
        "circonstances": ""
      }},
      "procedure": [
        {{"etape": "", "contexte": ""}}
      ],
      "scelles": [
        {{"description": ""}}
      ]
    }}

    Renvoie uniquement le JSON valide, sans explication ni texte autour.
    """

    last_error = None

    # --- Boucle sur les modèles candidats ---
    for model_name in MODEL_CANDIDATES:
        try:
            print(f"🧠 Utilisation du modèle Groq : {model_name}")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en analyse de procédures policières françaises. "
                                   "Tu extrais uniquement les faits, noms et dates pertinents."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2000,
            )

            raw_output = response.choices[0].message.content.strip()

            # --- Parsing JSON robuste ---
            try:
                return json.loads(raw_output)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", raw_output, re.S)
                if match:
                    return json.loads(match.group(0))
                else:
                    raise ValueError("Réponse non JSON du LLM.")

        except Exception as e:
            print(f"⚠️ Erreur avec {model_name} : {e}")
            last_error = e
            continue  # on passe au modèle suivant

    # --- Si tous les modèles échouent ---
    raise RuntimeError(f"Erreur LLM (Groq) : toutes les tentatives ont échoué. Dernière erreur : {last_error}")



# ============================================================
# 3️⃣ Interface principale
# ============================================================

def extraction_procedure(path: str, out_json: Optional[str] = None) -> dict:
    """
    Pipeline complet :
      - Conversion du fichier en texte brut
      - Extraction structurée via LLM Groq
      - Sauvegarde éventuelle au format JSON
    """
    print(f"🧾 Traitement du fichier : {path}")
    text = convert_to_txt(path)
    print("🤖 Envoi du texte au LLM Groq...")

    data = extract_with_llm(text, source_file=path)

    if out_json:
        with open(out_json, "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON sauvegardé dans : {out_json}")

    return data


# ============================================================
# 4️⃣ Test CLI
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python extraction_procedure.py fichier.docx|odt|txt [out.json]")
        sys.exit(1)

    input_path = sys.argv[1]
    out_json = sys.argv[2] if len(sys.argv) > 2 else None
    result = extraction_procedure(input_path, out_json)
    print(json.dumps(result, ensure_ascii=False, indent=2))
