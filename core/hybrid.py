"""Opt-in on-device hybrid retrieval. No embeddings or source text leave localhost."""
import json
import math
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from core.rag import retrieve


class HybridRetrievalError(ValueError):
    pass


def ollama_url() -> str:
    url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.username or parsed.password:
        raise HybridRetrievalError("Ollama doit utiliser une adresse HTTP locale (localhost).")
    return url


def local_embeddings(texts: list[str], *, model: str | None = None, opener=urlopen) -> list[list[float]]:
    if not texts:
        return []
    if len(texts) > 121 or sum(len(t) for t in texts) > 350000:
        raise HybridRetrievalError("Dossier trop volumineux pour les embeddings locaux.")
    payload = json.dumps({"model": model or os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"),
                          "input": texts}).encode("utf-8")
    request = Request(ollama_url() + "/api/embed", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with opener(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        embeddings = result["embeddings"]
        if len(embeddings) != len(texts) or not all(isinstance(e, list) and e and
                                                    all(isinstance(v, (float, int)) for v in e) for e in embeddings):
            raise ValueError("invalid embeddings")
        return embeddings
    except (URLError, HTTPError, ValueError, KeyError, TypeError, OSError) as exc:
        raise HybridRetrievalError("Embeddings Ollama indisponibles. Démarrez Ollama et installez le modèle configuré (par défaut bge-m3).") from None


def similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    return sum(x*y for x, y in zip(a, b)) / (norm_a * norm_b) if norm_a and norm_b else 0.0


def retrieve_hybrid(chunks: list[dict], question: str, limit: int = 6,
                    *, embedder=local_embeddings) -> list[dict]:
    """RRF of semantic cosine and BM25 rankings. Source IDs are unchanged."""
    if not chunks or not question.strip() or limit <= 0:
        return []
    if len(chunks) > 120:
        raise HybridRetrievalError("Limite : 120 fragments pour cette démonstration.")
    lexical = retrieve(chunks, question, limit=len(chunks))
    vectors = embedder([question] + [c["text"] for c in chunks])
    scores = [similarity(vectors[0], v) for v in vectors[1:]]
    sem_order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    # Reject embeddings unrelated to the query rather than treating every vector as evidence.
    sem_order = [i for i in sem_order if scores[i] > 0.12]
    ranks = {}
    for ranked in (lexical, [chunks[i] for i in sem_order]):
        for pos, item in enumerate(ranked):
            ranks[item["id"]] = ranks.get(item["id"], 0.0) + 1 / (60 + pos + 1)
    return sorted([c for c in chunks if c["id"] in ranks], key=lambda c: ranks[c["id"]], reverse=True)[:limit]
