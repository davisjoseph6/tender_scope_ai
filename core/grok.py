"""xAI Grok Responses API: structured extraction and source-verified RAG.

Grok (xAI) is unrelated to Groq. All network calls require a user action in the UI.
No provider error body or token is exposed to users.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values
from pydantic import ValidationError

from core.llm import Answer, CAT_LABELS, Extraction, LLMError, SYSTEM, validate_citations
from core.rag import chunk_pages, retrieve

API_URL = "https://api.x.ai/v1/responses"
DEFAULT_MODEL = "grok-4.7"
ROOT = Path(__file__).resolve().parents[1]


class GrokError(ValueError):
    """Safe error to display; never includes tokens or raw API responses."""


def grok_settings():
    local = dotenv_values(ROOT / ".env")
    return {
        "api_key": os.environ.get("XAI_API_KEY") or local.get("XAI_API_KEY") or "",
        "model": os.environ.get("XAI_MODEL") or local.get("XAI_MODEL") or DEFAULT_MODEL,
    }


def request_grok_json(schema, system, task, chunks, *, opener=urlopen, model=None):
    """Use current xAI Responses API with strict schema output; no tools/search enabled."""
    conf = grok_settings()
    if not conf["api_key"]:
        raise GrokError("Clé xAI absente : ajoutez XAI_API_KEY dans .env, sans la partager.")
    if not chunks or len(chunks) > 100 or sum(len(x.get("text", "")) for x in chunks) > 100000:
        raise GrokError("Entrée trop volumineuse ou vide ; divisez le dossier sans troncature silencieuse.")
    payload = {
        "model": model or conf["model"],
        "input": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps({"task": task, "sources": chunks}, ensure_ascii=False)},
        ],
        "text": {"format": {
            "type": "json_schema",
            "name": schema.__name__.lower(),
            "strict": True,
            "schema": schema.model_json_schema(),
        }},
        "store": False,
    }
    req = Request(API_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                  headers={"Authorization": "Bearer " + conf["api_key"],
                           "Content-Type": "application/json", "Accept": "application/json"},
                  method="POST")
    try:
        with opener(req, timeout=180) as response:
            result = json.loads(response.read(2_000_000).decode("utf-8"))
    except HTTPError as error:
        if error.code == 401:
            raise GrokError("xAI HTTP 401 : clé XAI_API_KEY incorrecte ou révoquée.") from None
        if error.code == 403:
            raise GrokError("xAI HTTP 403 : clé ou modèle non autorisé dans votre compte xAI.") from None
        if error.code == 429:
            raise GrokError("xAI HTTP 429 : limite de requêtes ou de crédits ; relancez plus tard.") from None
        if error.code == 400:
            raise GrokError("xAI HTTP 400 : vérifier XAI_MODEL et la prise en charge du JSON structuré.") from None
        raise GrokError(f"xAI HTTP {error.code} : requête échouée sans nouveau résultat.") from None
    except (URLError, OSError, UnicodeError, json.JSONDecodeError):
        raise GrokError("Connexion xAI impossible ou réponse réseau invalide.") from None
    try:
        if result.get("status") != "completed" or result.get("error"):
            raise ValueError("incomplete generation")
        texts = [
            part["text"]
            for message in result["output"]
            if message.get("type") == "message"
            for part in message.get("content", [])
            if part.get("type") == "output_text" and isinstance(part.get("text"), str)
        ]
        if len(texts) != 1:
            raise ValueError("ambiguous response")
        return schema.model_validate_json(texts[0])
    except (KeyError, TypeError, ValueError, ValidationError):
        raise GrokError("Sortie xAI absente, incomplète ou non conforme au schéma ; résultat rejeté.") from None


TASK = (
    "Extrais les exigences et échéances explicites dans ce seul passage BOAMP ou document. "
    "Conserve le jour, mois, année ET heure dans chaque résumé d'échéance si présents. "
    "Préserve négations, conditions, alternatives et unités. N'invente aucune exigence. "
    "Une citation courte et exacte par exigence, avec le source_id fourni. "
    "Aucun verdict d'éligibilité. Si rien n'est exploitable, liste vide. "
    "Catégories admises (codes) : " + json.dumps(CAT_LABELS, ensure_ascii=False)
)


def extract_requirements_grok(pages, *, checkpoint=None, on_progress=None, generator=None):
    """Small batches and per-source citation validation; resume identical dossier/model."""
    chunks = chunk_pages(pages, size=1400, overlap=150)
    if not chunks:
        raise GrokError("Aucun texte exploitable dans ce dossier.")
    if len(chunks) > 60:
        raise GrokError("Ce mode accepte 60 fragments maximum pour contrôler le coût et le contexte.")
    model = grok_settings()["model"]
    fingerprint = hashlib.sha256(json.dumps(
        {"pages": pages, "model": model, "provider": "xai", "chunk_size": 1400},
        ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    saved = checkpoint if checkpoint and checkpoint.get("fingerprint") == fingerprint else {}
    next_chunk = int(saved.get("next_chunk", 0))
    if not 0 <= next_chunk <= len(chunks):
        saved, next_chunk = {}, 0
    findings = deepcopy(saved.get("findings", []))
    rejected = int(saved.get("rejected", 0))
    seen = {(item["category"], tuple((c["document"], c["page"], c["quote"]) for c in item["citations"]))
            for item in findings}
    generator = generator or request_grok_json
    for index in range(next_chunk, len(chunks)):
        batch = [chunks[index]]
        result = generator(Extraction, SYSTEM, TASK, batch)
        for item in result.requirements:
            try:
                citations = validate_citations(item.citations, batch)
            except LLMError:
                rejected += 1
                continue
            label = CAT_LABELS[item.category]
            identity = (label, tuple((c["document"], c["page"], c["quote"]) for c in citations))
            if identity not in seen:
                findings.append({"category": label, "summary": item.summary,
                                 "mandatory": item.mandatory, "citations": citations})
                seen.add(identity)
        if on_progress:
            on_progress({"fingerprint": fingerprint, "next_chunk": index + 1,
                         "total_chunks": len(chunks), "findings": deepcopy(findings),
                         "rejected": rejected})
    return {"requirements": findings, "rejected_requirements": rejected,
            "model": model, "mode": "Grok xAI · extraction structurée",
            "chunks_processed": len(chunks), "human_review_required": True,
            "pages_with_text": sum(bool(p["text"].strip()) for p in pages),
            "pages_without_text": sum(not p["text"].strip() for p in pages)}


def answer_question_grok(pages, question, *, generator=None):
    """BM25 -> cited xAI answer; no API call when the retrieval has no matches."""
    if not question.strip() or len(question) > 2000:
        raise GrokError("La question doit avoir entre 1 et 2000 caractères.")
    chunks = retrieve(chunk_pages(pages), question)
    if not chunks:
        return {"status": "Information insuffisante", "answer": "Aucun passage pertinent retrouvé par BM25.",
                "citations": [], "mode": "BM25 local · sans appel xAI"}
    response = (generator or request_grok_json)(Answer, SYSTEM,
        "Réponds à la question seulement avec les sources citées : " + question, chunks)
    if response.status == "Information insuffisante":
        return {"status": response.status, "answer": "Information insuffisante ; vérifier les pièces officielles.",
                "citations": [], "mode": "Grok xAI + BM25", "model": grok_settings()["model"]}
    citations = validate_citations(response.citations, chunks)
    return {"status": response.status, "answer": response.answer,
            "citations": citations, "mode": "Grok xAI + BM25", "model": grok_settings()["model"]}
