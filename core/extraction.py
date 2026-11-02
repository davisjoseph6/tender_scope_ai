"""Repérage de passages candidats, sans interprétation juridique ou LLM."""
import re

from core.doc_types import normalize

RULES = {
    "Date limite": r"date limite|date et heure limites?|remise des offres|reception des offres",
    "Critères de sélection": r"criteres? (?:d.attribution|de selection)|ponderation|valeur technique",
    "Chiffre d’affaires": r"chiffre d.affaires|capacite economique",
    "Certifications": r"\biso\s*\d+|certification|qualification professionnelle",
    "Références": r"references|prestations similaires",
    "Pièces de candidature": r"\bdc1\b|\bdc2\b|\bdume\b|documents? (?:a fournir|obligatoires?)",
    "Clauses sensibles": r"penalites?|resiliation|delai[s]? de paiement|responsabilite|retenue de garantie",
}


def extract_key_info(pages: list[dict]) -> list[dict]:
    """Retourne une citation exacte par catégorie et ligne ; absence ≠ absence d’exigence."""
    findings = []
    for page in pages:
        lines = page["text"].splitlines()
        for index, line in enumerate(lines):
            for category, pattern in RULES.items():
                if re.search(pattern, normalize(line)):
                    findings.append({
                        "category": category,
                        "document": page["document"],
                        "page": page["page"],
                        "quote": "\n".join(lines[max(0, index - 1):index + 3]),
                    })
    return findings
