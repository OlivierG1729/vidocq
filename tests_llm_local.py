import json, subprocess, textwrap, time

MODELS = ["tinyllama:latest", "phi3:mini", "phi3:latest", "granite-code:3b"]

TEXT = """Deux personnes ont été interpellées à Paris dans l'enquête sur le casse du Louvre.
L'une d'elles, une femme de 38 ans de La Courneuve, est accusée de complicité.
Le ministre de l'Intérieur Laurent Nunez a réagi depuis Marseille."""

PROMPT = textwrap.dedent(f"""
Tu es un analyste francophone.
À partir du texte suivant, produis une liste JSON des événements décrits avec les clés :
[
  {{
    "lieu": "ville, pays ou lieu précis",
    "moment": "date ou période (si connue)",
    "personnes": ["noms des personnes"],
    "resume": "bref résumé de l'événement"
  }}
]

Réponds UNIQUEMENT en JSON :
\"\"\"{TEXT}\"\"\"
""")

for model in MODELS:
    print(f"\n=== 🧠 Test du modèle : {model} ===")
    t0 = time.time()
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=PROMPT.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45
        )
        duration = time.time() - t0
        output = result.stdout.decode("utf-8", errors="ignore")
        print(f"⏱️ Durée : {duration:.1f}s")
        print("📝 Sortie brute :")
        print(output[:400])  # on affiche seulement les 400 premiers caractères
        try:
            start, end = output.find("["), output.rfind("]") + 1
            data = json.loads(output[start:end])
            print("✅ JSON valide détecté !")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print("⚠️ Pas de JSON valide.")
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout (>45s) pour {model}")
