from event_map import _GEOCODER, _call_llm, _context_for_location, _split_sentences
import time

# Exemple minimal
text = "Un accident est survenu à Marseille le 5 mai 2023. La police est intervenue sur place."
sentences = _split_sentences(text)
context = _context_for_location(sentences, "Marseille")

# --- TEST A : géocodage ---
print("⏱️ Test A : géocodage…")
t0 = time.time()
coords = _GEOCODER.geocode("Marseille")
print(f"Résultat : {coords}, durée = {time.time()-t0:.2f}s")

# --- TEST B : appel LLM ---
print("\n⏱️ Test B : appel LLM…")
t0 = time.time()
data = _call_llm("doc1", "Marseille", context)
print(f"Résultat : {data}, durée = {time.time()-t0:.2f}s")
