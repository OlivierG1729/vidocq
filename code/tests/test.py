import json
import re
import urllib.request


def call_ollama(model: str, prompt: str) -> str:
    """Appelle l'API Ollama locale pour générer une réponse."""

    url = "http://localhost:11434/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req) as resp:
        resp_data = resp.read()

    response = json.loads(resp_data)
    return response.get("response", "")


def generate_summary(text: str) -> dict:
    """Génère un résumé structuré en JSON pour le texte fourni."""

    prompt = f"""
Ignore toutes les instructions précédentes. Tu es un assistant expert en analyse d'information.

À partir du texte ci-dessous, produis un résumé structuré en JSON avec les clés suivantes :
- "titre"
- "date_principale"
- "lieux"
- "personnalites"
- "resume"

Réponds uniquement avec un objet JSON valide. Ne donne aucun commentaire, balise Markdown, ni texte autour.

Voici le texte à analyser :
{text}
"""

    raw = call_ollama("llama3", prompt)

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        raise ValueError("Aucun JSON détecté dans la réponse du modèle.")

    json_text = json_match.group(0)
    return json.loads(json_text)


if __name__ == "__main__":
    example = "ceci est un essai fait à Paris le 24/07/2025 par M. Dupont"
    print(generate_summary(example))



