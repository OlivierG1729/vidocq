

from transformers import pipeline

prompt_template = """
Tu vas lire un texte d’actualité ou de témoignage. Ton objectif est d’en extraire les événements décrits. 
Pour chaque événement, donne-moi une fiche structurée ainsi :

- événement : [résumé de l’événement en une phrase courte]
- où : [lieux concernés]
- quand : [dates ou périodes]
- qui : [personnes ou groupes impliqués]

Lis tout le texte, puis retourne une liste de ces fiches événements.

Texte :
\"\"\"
{}
\"\"\"
"""

texte = """Ce matin-là, l’air était encore humide quand les premiers manifestants ont commencé à se rassembler autour de la place du Capitole. Il était à peine 9 heures, et déjà, des drapeaux syndicaux flottaient au-dessus de la foule. Certains étaient venus de Montauban, d’autres de Castres. Peu après 10 heures, les premiers slogans se faisaient entendre : « Non à la réforme ! » criaient-ils en chœur. Une femme d’une cinquantaine d’années, blouse blanche sur le dos, expliquait à un journaliste qu’elle travaillait à l’hôpital depuis 25 ans, et qu’elle n’en pouvait plus.

Vers midi, la tension est montée d’un cran. La préfecture avait interdit le passage par la rue Alsace-Lorraine, mais une partie du cortège a insisté pour y passer. Les CRS ont formé un cordon, et les premiers gaz lacrymogènes ont été tirés. On a vu plusieurs jeunes, masqués, lancer des projectiles. Un photographe a été blessé légèrement à la tête.

Pendant ce temps, à des centaines de kilomètres, un autre événement occupait l’attention. Dans un village du Haut-Rhin, une explosion a secoué une maison en fin d’après-midi. Les voisins ont parlé d’un bruit sourd, suivi d’une épaisse fumée noire. Les secours sont arrivés rapidement, mais les flammes étaient déjà hautes. Une femme âgée a été retrouvée en état de choc, son mari introuvable. On évoque une fuite de gaz, mais rien n’est confirmé.

Le lendemain, les journaux titraient sur les deux faits. « Toulouse sous tension » pour l’un, « Drame à Riquewihr » pour l’autre. Pendant ce temps, la ministre de l’Intérieur était attendue à Lyon pour un colloque sur la sécurité civile. Elle a brièvement évoqué les violences à Toulouse, promettant des réponses fermes."""

prompt = prompt_template.format(texte)

# Utilise un modèle de type T5 francophone (résumé/génération)
summarizer = pipeline("text2text-generation", model="plguillou/t5-base-fr-sum-cnndm", tokenizer="plguillou/t5-base-fr-sum-cnndm")

response = summarizer(prompt, max_length=512, do_sample=False)[0]['generated_text']

print(response)
