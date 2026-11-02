"""Recherche lexicale locale ; ne génère aucune réponse avec un LLM."""
import re

from core.doc_types import normalize

STOPWORDS = set("a au aux avec ce ces cette comment dans de des du elle en est et etre il je la le les leur ma mes mon ne nous on ou par pas plus pour pouvez quel quelle quelles quels que qui sa se ses son sont sur un une vous y doit sont sont dois puis quelles quelle concernant obligatoire".split())


def search_passages(pages: list[dict], query: str, limit: int = 5) -> list[dict]:
    terms = {t for t in re.findall(r"\w+", normalize(query)) if len(t) > 2 and t not in STOPWORDS}
    if not terms:
        return []
    results = []
    for page in pages:
        lines = page["text"].splitlines()
        best = None
        for index in range(len(lines)):
            quote = "\n".join(lines[max(0, index - 1):index + 3])
            words = set(re.findall(r"\w+", normalize(quote)))
            matched = len(terms & words)
            if matched and (best is None or matched > best["matches"]):
                best = {"document": page["document"], "page": page["page"], "quote": quote, "matches": matched}
        if best:
            results.append(best)
    return sorted(results, key=lambda r: r["matches"], reverse=True)[:limit]
