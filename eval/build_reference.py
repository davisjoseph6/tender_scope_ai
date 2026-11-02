"""Matérialise les 20 annotations ci-dessous et vérifie leurs citations dans le PDF local.

Les attentes sont rédigées pour cette version du RC, sans interprétation du droit actuel.
Ne pas modifier cette référence simplement pour faire passer une nouvelle extraction.
"""
import hashlib
import json
from pathlib import Path
import re

from core.pdf_reader import extract_pages

ROOT = Path(__file__).resolve().parent
PDF = ROOT.parent / "data/samples/RC_Coeur_Herault_2024.pdf"
DOC = PDF.name

# Sujet, page, passage, réponse attendue, catégories acceptables.
ANNOTATIONS = [
    ("Dépôt des offres", 1, "DATE LIMITE DE REMISE DES OFFRES : Jeudi 01/08/2024 à 11 h", "Dépôt au 1er août 2024 à 11 h ; marché ancien utilisé pour tester le logiciel.", ["Date limite"]),
    ("Validité des offres", 2, "Durée de validité des offres 90 jours", "Validité de 90 jours, à distinguer de l’échéance de dépôt.", ["Durées et calendrier", "Autre"]),
    ("Durée du marché", 1, "Le marché est conclu pour une période d'une année, renouvelable deux fois par tacite reconduction, soit une durée maximum de trois ans.", "Une année, deux reconductions possibles, trois ans maximum.", ["Durées et calendrier", "Autre"]),
    ("Résiliation", 1, "Il pourra être résilié par la collectivité deux mois au moins avant chaque échéance annuelle, par lettre recommandée avec avis de réception.", "Faculté de résiliation avec préavis d’au moins deux mois : clause contractuelle, pas tâche technique.", ["Clauses sensibles"]),
    ("Sous-traitance", 1, "La sous-traitance est refusée.", "Le RC indique un refus de la sous-traitance ; rapprocher cette phrase des demandes DC4 page 3.", ["Clauses sensibles", "Conditions de candidature", "Autre"]),
    ("Langue de réponse", 2, "L’offre devra être rédigée uniquement en langue française.", "Offre en français ; modalité de réponse, pas prestation technique.", ["Modalités de réponse", "Autre"]),
    ("Lettre de candidature", 3, "Lettre de candidature ou Imprimé DC1;", "Lettre de candidature OU DC1 : préserver l’alternative.", ["Pièces de candidature"]),
    ("Jugements conditionnels", 3, "Copie du ou des jugements prononcés si le candidat est en redressement judiciaire", "Pièce demandée si le candidat est en redressement judiciaire. Applicabilité à vérifier pour l’entreprise.", ["Pièces de candidature"]),
    ("Qualifications conditionnelles", 3, "Certificats de qualifications professionnelles le cas échéant", "Certificats le cas échéant, sans inventer une certification ISO universellement obligatoire.", ["Pièces de candidature", "Certifications"]),
    ("Déclaration de chiffre d’affaires", 3, "Déclaration concernant le chiffre d'affaires global voire le chiffre d'affaires concernant les prestations intellectuelles objet du marché, réalisées au cours des trois derniers exercices disponibles", "Déclaration sur les trois derniers exercices disponibles ; ce passage ne donne aucun seuil minimal.", ["Pièces de candidature", "Chiffre d’affaires"]),
    ("Références", 3, "Liste des principales références pour des prestations similaires exécutées ou en cours d'exécution au cours des trois dernières années", "Références similaires sur trois ans, avec montant, date et destinataire. Aucun nombre minimum ne doit être inventé.", ["Pièces de candidature", "Références"]),
    ("Mémoire technique", 3, "Le mémoire technique et méthodologique relatif à la mission et permettant de juger la valeur technique de l’offre", "Mémoire à remettre dans l’offre, avec méthodologie, équipe et proposition de contrat.", ["Pièces de candidature", "Pièces de l’offre"]),
    ("Pondération du prix", 4, "Le prix de la prestation annuelle 45%", "Prix : 45 % dans le tableau principal de jugement.", ["Critères de sélection"]),
    ("Pondération technique", 4, "La valeur technique du candidat suivant les capacités ou les justificatifs fournis 40%", "Valeur technique : 40 % dans le tableau principal.", ["Critères de sélection"]),
    ("Pondération intervention", 4, "La capacité à intervenir suivant l’Article I – Conditions d’intervention du CCTP 15%", "Capacité à intervenir : 15 % dans le tableau principal.", ["Critères de sélection"]),
    ("Sous-critères techniques", 4, "Pertinence de la méthodologie proposée (20%)", "Méthodologie 20 %, moyens/livrables 10 %, planning 10 %. Le texte annonce quatre sous-critères mais en liste trois : incohérence à signaler.", ["Critères de sélection"]),
    ("Négation sur le surcoût", 5, "Un changement éventuel du lieu de réalisation de la prestation ne saurait entrainer de surcoût, notamment au titre des déplacements.", "Le changement de lieu ne doit PAS entraîner de surcoût ; le résumé ne doit pas inverser la négation.", ["Clauses sensibles", "Conditions financières", "Autre"]),
    ("Variantes", 2, "Variantes non autorisées", "Les variantes sont indiquées comme non autorisées.", ["Modalités de réponse", "Conditions de candidature", "Autre"]),
    ("Négociation éventuelle", 4, "le pouvoir adjudicateur pourra négocier avec les candidats dont l’offre aura été classée dans les 3 premières places", "La négociation est une possibilité de l’acheteur, pas une obligation de négocier ni une promesse de sélection.", ["Procédure", "Autre"]),
    ("Incohérence du barème prix", 5, "L’offre la plus basse obtient la note maximale de 50/50.", "Le tableau page 4 annonce 45 % pour le prix, la méthode page 5 indique 50/50. Signaler l’écart sans le résoudre arbitrairement.", ["Critères de sélection", "Clauses sensibles", "Contradictions"]),
]


def build():
    data = PDF.read_bytes()
    pages = extract_pages(data, DOC)
    rows = []
    for index, (topic, page, phrase, expected, categories) in enumerate(ANNOTATIONS, start=1):
        match = re.search(r"\s+".join(re.escape(word) for word in phrase.split()), pages[page - 1]["text"])
        if match is None:
            raise ValueError(f"Citation non retrouvée : {topic}")
        row = {"id": f"rc{index:02}", "topic": topic, "document": DOC,
               "pdf_sha256": hashlib.sha256(data).hexdigest(), "expected": expected,
               "accepted_categories": categories, "sources": [{"page": page, "quote": match.group(), "anchor": phrase}],
               "annotation_status": "Référence initiale rédigée et vérifiée contre le texte ; validation indépendante par l’équipe requise"}
        if index in (8, 9):
            row["conditional"] = True
            row["required_summary_patterns"] = [["si .*redressement|le cas échéant|applicab|condition", "Condition d’applicabilité non exprimée dans le résumé"]]
        if index == 17:
            row["forbidden_summary_patterns"] = [[r"peut entra[îi]ner(?: un| de)? surco[uû]t", "Sens inversé : le résumé autorise un surcoût que la citation exclut"]]
            row["required_summary_patterns"] = [[r"ne .*surco[uû]t|sans surco[uû]t|aucun surco[uû]t|pas .*surco[uû]t|surco[uû]t.*(?:interdit|exclu)", "La négation sur le surcoût n’est pas conservée"]]
        if index == 20:
            row["required_summary_patterns"] = [[r"45\s*%", "Le résumé ne rapproche pas la méthode de notation des 45 % de la page 4"]]
        rows.append(row)
    (ROOT / "gold_rc.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} cas de référence ; toutes les citations retrouvées dans le PDF.")


if __name__ == "__main__":
    build()
