


def generate_summary(text: str) -> dict:
    prompt = f"""
    Tu es un assistant expert en analyse d'information.

    À partir du texte ci-dessous, produis un résumé structuré en JSON avec les clés suivantes :
    - "titre"
    - "date_principale"
    - "lieux"
    - "personnalites"
    - "resume"

    Voici le texte à analyser :
    {text}
    """
    raw = call_ollama("llama3", prompt)
    
    # Nettoyage du bloc JSON éventuel
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        raise ValueError("Aucun JSON détecté dans la réponse du modèle.")
    
    json_text = json_match.group(0)
    return json.loads(json_text)


text = "ceci est un essai fait à Paris le 24/07/2025 par M. Dupont"
generate_summary(text)






import re
import json

def call_ollama(model: str, prompt: str) -> str:
    # ⛔️ À remplacer par ton appel réel au modèle LLaMA via Ollama ou autre
    raise NotImplementedError("À implémenter : appel réel à ton modèle")

def generate_summary(text: str) -> dict:
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

    # Nettoyage : extraire premier bloc JSON
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        raise ValueError("Aucun JSON détecté dans la réponse du modèle.")
    
    json_text = json_match.group(0)
    return json.loads(json_text)

text = "ceci est un essai fait à Paris le 24/07/2025 par M. Dupont"
generate_summary(text)



