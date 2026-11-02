"""Reproducible *prompt-only* single-pass baseline, on full RC pages without retrieval.

Run on machine with configured Groq, or local Ollama:
  python -m eval.run_prompt_only --backend groq
  python -m eval.run_prompt_only --backend ollama
Then compare with: python -m eval.field_metrics --compare eval/prompt_only_groq.json
"""
import argparse
import json
from pathlib import Path

from core.pdf_reader import extract_pages
from core.llm import Extraction, CAT_LABELS, SYSTEM, request_structured, validate_citations, LLMError, settings
from core.local_llm import request_local_json

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("groq", "ollama"), default="groq")
    parser.add_argument("--pdf", type=Path, default=ROOT.parent / "data/samples/RC_Coeur_Herault_2024.pdf")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = args.pdf.read_bytes()
    pages = extract_pages(data, args.pdf.name)
    sources = [{"id": f"p{idx}", **page} for idx, page in enumerate(pages, 1) if page["text"].strip()]
    chars = sum(len(c["text"]) for c in sources)
    if not sources or chars > 100000:
        parser.error(f"Le RC est vide ou trop long ({chars} caractères); aucune troncature automatique.")
    task = ("PROMPT-ONLY CONTROL. You have the entire consultation regulation as input, no retrieval, "
            "no embeddings, no reranking. Extract explicit requirements and factual deadlines "
            "as short summaries with exact source quotes and corresponding source_id. "
            "One requirement per element. Preserve negations, conditionality and units. "
            "Do not invent. If a field is missing, omit it. "
            "Use categories from this dictionary only: "
            + json.dumps(CAT_LABELS, ensure_ascii=False))
    if args.backend == "groq":
        result = request_structured(Extraction, task, sources, max_tokens=12000)
        model = settings()["model"]
    else:
        result = request_local_json(Extraction, SYSTEM, task, sources)
        import os
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    findings = []
    rejected = 0
    for item in result.requirements:
        try:
            citations = validate_citations(item.citations, sources)
        except LLMError:
            rejected += 1
            continue
        findings.append({"category": CAT_LABELS[item.category], "summary": item.summary,
                         "mandatory": item.mandatory, "citations": citations})
    payload = {"mode": f"PROMPT_ONLY_FULL_DOCUMENT_{args.backend.upper()}", "model": model,
               "requirements": findings, "rejected_requirements": rejected,
               "source_pdf": args.pdf.name, "all_pages_supplied": len(sources),
               "note": "One full-document model call; no RAG, no chunking, no fine-tuning. Reproducible only at recorded model and prompt version."}
    output = args.output or ROOT / ("prompt_only_groq.json" if args.backend == "groq" else "prompt_only_ollama.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(findings)} sourced requirements to {output}; {rejected} rejected.")


if __name__ == "__main__":
    main()
