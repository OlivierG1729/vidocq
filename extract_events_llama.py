import json, subprocess, textwrap, time, sys
from pathlib import Path
from multiprocessing import Pool, cpu_count

MODEL = "llama3:latest"  # résultats satisfaisaint mais très lent (6 min pour un texte de 30 lignes)
# MODEL = "tinyllama:latest"  # rapide mais résultats très mauvais
# MODEL = "mistral:7b-instruct-q4_K_M"  # bcp trop lent et pas très bon
# MODEL = "phi3:mini"   # très lent
import json, subprocess, textwrap, time, sys
from pathlib import Path

MODEL = "llama3:latest"  # ou autre modèle local via Ollama
CHUNK_SIZE = 500         # pour éviter les prompts trop longs
TIMEOUT = 240              # en secondes

# -------------------------------------------------------------------
# ⚙️ Fonction d'appel à Ollama
def run_ollama(model: str, prompt: str) -> list:
    """Appelle Ollama en ligne de commande et tente d'extraire une liste JSON de quadruplets."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
        )
        output = result.stdout.decode("utf-8", errors="ignore")

        # Recherche du JSON dans la réponse
        start, end = output.find("["), output.rfind("]") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(output[start:end])
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass
        print("⚠️ JSON non valide, sortie brute (début) :\n", output[:400])
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout (> {TIMEOUT}s)")
    except Exception as e:
        print(f"⚠️ Erreur d’exécution : {e}")
    return []

# -------------------------------------------------------------------
# 🧩 Fonction principale
def extract_events_from_file(filepath: Path):
    if not filepath.exists():
        print(f"❌ Fichier introuvable : {filepath}")
        sys.exit(1)

    text = filepath.read_text(encoding="utf-8", errors="ignore")
    chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    print(f"📄 Texte chargé ({len(text)} caractères, {len(chunks)} segments)")

    all_events = []

    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n=== 🔍 Segment {idx}/{len(chunks)} ===")

        prompt = textwrap.dedent(f"""
        Tu es un analyste d'investigation francophone.
        À partir du texte suivant, identifie tous les événements distincts décrits,
        et pour chacun, produis un quadruplet JSON de la forme :
        [
          {{
            "ou": "lieu précis (ville, adresse, lieu public...)",
            "quand": "date ou heure (format texte libre)",
            "qui": ["personnes ou groupes impliqués"],
            "quoi": "résumé très concis de l'événement"
          }}
        ]
        Réponds UNIQUEMENT avec un JSON valide (sans introduction, ni commentaire).

        Texte :
        \"\"\"{chunk}\"\"\"
        """)

        t0 = time.time()
        events = run_ollama(MODEL, prompt)
        print(f"⏱️ Durée : {time.time() - t0:.1f}s — {len(events)} événements détectés")
        all_events.extend(events)

    # ✅ Sauvegarde finale
    outpath = filepath.with_suffix(".events.json")
    outpath.write_text(json.dumps(all_events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Résultats enregistrés dans : {outpath}")

# -------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python extract_events_llama.py <fichier.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    extract_events_from_file(file_path)
