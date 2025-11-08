import json, subprocess, textwrap, time, sys
from pathlib import Path

MODEL = "tinyllama:latest"
CHUNK_SIZE = 2000  # caractères maximum par prompt
TIMEOUT = 90       # secondes max par appel

# -------------------------------------------------------------------
# 🧩 Fonction utilitaire pour exécuter un prompt avec Ollama
def run_ollama(model: str, prompt: str) -> list:
    payload = prompt.encode("utf-8")
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
        )
        output = result.stdout.decode("utf-8", errors="ignore")
        start, end = output.find("["), output.rfind("]") + 1
        if start != -1 and end != 0:
            data = json.loads(output[start:end])
            if isinstance(data, list):
                return data
        print("⚠️ JSON non valide, sortie brute :\n", output[:500])
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout (> {TIMEOUT}s)")
    except Exception as e:
        print(f"⚠️ Erreur d'exécution : {e}")
    return []

# -------------------------------------------------------------------
# 🧩 Fonction principale
def analyze_text_with_granite(filepath: Path):
    if not filepath.exists():
        print(f"❌ Fichier introuvable : {filepath}")
        sys.exit(1)

    text = filepath.read_text(encoding="utf-8", errors="ignore")
    chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
    print(f"📄 Texte chargé ({len(text)} caractères, {len(chunks)} segments)")

    all_events = []

    for idx, chunk in enumerate(chunks, start=1):
        print(f"\n=== 🔍 Traitement du segment {idx}/{len(chunks)} ===")
        prompt = textwrap.dedent(f"""
        Tu es un analyste d'investigation francophone.
        À partir du texte suivant, identifie les événements importants et résume-les sous forme de liste JSON
        avec les champs suivants :
        [
          {{
            "lieu": "nom du lieu précis (ville, musée, pays...)",
            "moment": "date ou période mentionnée",
            "personnes": ["personnes impliquées (nom ou rôle explicite)"],
            "resume": "résumé factuel de l'événement"
          }}
        ]
        Réponds UNIQUEMENT avec un JSON valide :
        \"\"\"{chunk}\"\"\"
        """).strip()

        t0 = time.time()
        events = run_ollama(MODEL, prompt)
        print(f"⏱️ Durée : {time.time() - t0:.1f}s — {len(events)} événements détectés")
        all_events.extend(events)

    # ✅ Résumé global
    print("\n=== ✅ Résumé final ===")
    print(json.dumps(all_events, indent=2, ensure_ascii=False))
    outpath = filepath.with_suffix(".events.json")
    outpath.write_text(json.dumps(all_events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Résultats enregistrés dans : {outpath}")

# -------------------------------------------------------------------
# 🧩 Exécution principale
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python test_granite_from_file.py <fichier.txt>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    analyze_text_with_granite(file_path)
