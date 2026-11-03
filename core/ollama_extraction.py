"""Citation-checked local extraction for small dossiers. No Groq dependency."""
import hashlib
import json
import os
from copy import deepcopy

from core.llm import CAT_LABELS, Extraction, SYSTEM, LLMError, validate_citations
from core.local_llm import request_local_json
from core.rag import chunk_pages

TASK = (
    "Lis uniquement ce fragment de l'avis BOAMP ou document fourni. "
    "Extrais chaque exigence explicite dans requirements. Pour une date limite, "
    "COPIE la valeur précise (jour/mois/année ET heure si présentes) dans summary. "
    "Ne transforme jamais une date de validité de l'offre en date limite de dépôt. "
    "Préserve les négations, les conditions et les alternatives. "
    "Retourne une liste vide si le fragment n'a aucune exigence. "
    "Chaque élément doit citer un passage exact et continu avec le bon source_id. "
    "Ne considère pas la présence d'une citation comme la preuve que ton résumé est vrai. "
    "Aucun verdict d'éligibilité ou de conformité. Utilise les codes de catégorie suivants : "
    + json.dumps(CAT_LABELS, ensure_ascii=False)
)


def extract_requirements_ollama(pages, *, checkpoint=None, on_progress=None, generator=None):
    """Single-chunk calls for limited Ollama contexts; resume only identical input/model."""
    chunks = chunk_pages(pages, size=1400, overlap=150)
    if not chunks:
        raise LLMError("Aucun passage lisible ; vérifiez les documents ou l'OCR.")
    if len(chunks) > 60:
        raise LLMError("Analyse Ollama limitée à 60 fragments pour cette démo ; divisez le dossier.")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    fingerprint = hashlib.sha256(json.dumps({"pages": pages, "model": model, "chunk_size": 1400},
                                           ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    saved = checkpoint if checkpoint and checkpoint.get("fingerprint") == fingerprint else {}
    next_chunk = int(saved.get("next_chunk", 0))
    if not 0 <= next_chunk <= len(chunks):
        saved, next_chunk = {}, 0
    findings = deepcopy(saved.get("findings", []))
    rejected = int(saved.get("rejected", 0))
    seen = {(item["category"], tuple((c["document"], c["page"], c["quote"])
              for c in item["citations"])) for item in findings}
    generator = generator or request_local_json
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
            key = (label, tuple((c["document"], c["page"], c["quote"]) for c in citations))
            if key not in seen:
                findings.append({"category": label, "summary": item.summary,
                                 "mandatory": item.mandatory, "citations": citations})
                seen.add(key)
        if on_progress:
            on_progress({"fingerprint": fingerprint, "findings": deepcopy(findings),
                         "rejected": rejected, "next_chunk": index + 1, "total_chunks": len(chunks)})
    return {"requirements": findings, "rejected_requirements": rejected, "model": model,
            "chunks_processed": len(chunks),
            "pages_without_text": sum(not p["text"].strip() for p in pages),
            "pages_with_text": sum(bool(p["text"].strip()) for p in pages),
            "mode": "Ollama local · extraction structurée", "human_review_required": True}
