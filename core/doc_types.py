"""Détection indicative : le contenu est prioritaire sur le nom du fichier."""
import re
import unicodedata


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


TYPES = {
    "RC": "reglement de la consultation|reglement de consultation",
    "CCTP": "cahier des clauses techniques particulieres",
    "CCAP": "cahier des clauses administratives particulieres",
    "AE": "acte d.engagement",
    "BOAMP": "avis de marche|avis d.appel public a la concurrence",
}


def detect_doc_type(filename: str, text: str = "") -> str:
    content = normalize(text[:8000])
    matches = [kind for kind, pattern in TYPES.items() if re.search(pattern, content)]
    if len(matches) == 1:
        return matches[0]
    name = normalize(filename).replace("_", " ")
    matches = [kind for kind, pattern in TYPES.items() if re.search(rf"\b{kind.lower()}\b|{pattern}", name)]
    return matches[0] if len(matches) == 1 else "À vérifier"
