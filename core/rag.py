"""Découpage par page et récupération BM25 locale, sans embeddings."""
from collections import Counter
import math
import re

from core.doc_types import normalize
from core.search import STOPWORDS


def chunk_pages(pages: list[dict], size: int = 2400, overlap: int = 300) -> list[dict]:
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Taille ou chevauchement de fragments invalide.")
    chunks = []
    for page in pages:
        text = page["text"]
        for start in range(0, len(text), size - overlap):
            quote = text[start:start + size]
            if quote.strip():
                chunks.append({"id": f"s{len(chunks) + 1}", "document": page["document"], "page": page["page"], "text": quote})
            if start + size >= len(text):
                break
    return chunks


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", normalize(text)) if len(t) > 1 and t not in STOPWORDS]


def retrieve(chunks: list[dict], question: str, limit: int = 6) -> list[dict]:
    """Classement BM25 ; aucun appel réseau, pas de résultat sans mot commun."""
    query = set(tokens(question))
    if not chunks or not query or limit <= 0:
        return []
    counts = [Counter(tokens(c["text"])) for c in chunks]
    lengths = [sum(c.values()) for c in counts]
    average = sum(lengths) / len(lengths) or 1
    frequency = {t: sum(t in count for count in counts) for t in query}
    scored = []
    for chunk, count, length in zip(chunks, counts, lengths):
        score = 0
        for term in query:
            tf = count[term]
            idf = math.log(1 + (len(chunks) - frequency[term] + 0.5) / (frequency[term] + 0.5))
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * length / average))
        if score > 0:
            scored.append((score, chunk))
    return [chunk for _, chunk in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]
