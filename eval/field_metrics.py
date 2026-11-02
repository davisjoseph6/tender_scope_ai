"""Strict automated proxy for field accuracy: historical, one-dossier gold.

Usage:
 python -m eval.field_metrics --prediction eval/baseline_rc.json
 python -m eval.field_metrics --prediction eval/baseline_rc.json --compare eval/prompt_only_groq.json
A correct field requires all its frozen value phrases in one summary AND a matching,
existing PDF citation on the gold page. No human semantics or model grading claimed.
"""
import argparse
import hashlib
import json
import re
import unicodedata
from math import sqrt
from pathlib import Path

from core.pdf_reader import extract_pages
from eval.evaluate import check_reference

ROOT = Path(__file__).resolve().parent


def normalized(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", str(text).lower())
                          if not unicodedata.combining(c)).split())


def wilson(success: int, total: int, z: float = 1.96):
    if not total:
        return None
    p = success / total
    denom = 1 + z * z / total
    mid = (p + z * z / (2 * total)) / denom
    margin = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [round(max(0, mid - margin), 4), round(min(1, mid + margin), 4)]


def score(cases, checks, prediction, pages):
    by_page = {(page["document"], page["page"]): page["text"] for page in pages}
    items = prediction.get("requirements", [])
    if not isinstance(items, list):
        raise ValueError("Format de prédiction invalide : requirements doit être une liste.")
    rows = []
    for case in cases:
        candidates = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            summary = normalized(item.get("summary", ""))
            # A quote on the right page must exist in the original PDF and cover
            # the case's frozen citation anchor, not merely share a keyword.
            source_valid = False
            for citation in item.get("citations", []):
                if not isinstance(citation, dict):
                    continue
                doc, page_num, quote = citation.get("document"), citation.get("page"), citation.get("quote", "")
                page_text = by_page.get((doc, page_num), "")
                if not quote or quote not in page_text or doc != case["document"]:
                    continue
                if any(page_num == source["page"]
                       and normalized(source["anchor"]) in normalized(quote)
                       for source in case["sources"]):
                    source_valid = True
                    break
            if source_valid:
                candidates.append({"item": idx + 1,
                                   "value_check": all(normalized(phrase) in summary
                                                      for phrase in checks[case["id"]]),
                                   "category_check": item.get("category") in case["accepted_categories"]})
        rows.append({"id": case["id"], "topic": case["topic"],
                     "source_supported": bool(candidates),
                     "field_value_and_source": any(c["value_check"] for c in candidates),
                     "category_and_source": any(c["category_check"] for c in candidates),
                     "candidate_items": [c["item"] for c in candidates]})
    n = len(rows)
    def metric(field):
        k = sum(bool(row[field]) for row in rows)
        return {"correct": k, "total": n, "rate": round(k / n, 4) if n else None,
                "wilson_95": wilson(k, n)}
    # Gold rc01 contains an exact deadline with date and time. A field summary
    # must retain both; finding the date only in a citation does not count.
    deadline_cases = [row for row in rows if row["id"] == "rc01"]
    d = sum(row["field_value_and_source"] for row in deadline_cases)
    return {"method": "strict_string_field_proxy_v1", "prediction_mode": prediction.get("mode", "not-recorded"),
            "model": prediction.get("model", "not-recorded"),
            "source_coverage": metric("source_supported"),
            "field_correct_and_source_supported": metric("field_value_and_source"),
            "category_correct_and_source_supported": metric("category_and_source"),
            "deadline_exact_match": {"correct": d, "total": len(deadline_cases),
                 "rate": d / len(deadline_cases) if deadline_cases else None,
                 "wilson_95": wilson(d, len(deadline_cases))},
            "rows": rows,
            "limitations": [
                "Automated exact phrase proxy, not validated semantic field accuracy.",
                "20 field questions and one deadline from ONE historical tender; Wilson intervals are descriptive only, not estimates of cross-tender generalisation.",
                "Correct quotations may support wrong interpretations; independent human annotation and multiple tenders still required.",
                "This historical structured Groq export is NOT a prompt-only baseline.",
            ]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prediction", type=Path, default=ROOT / "baseline_rc.json")
    p.add_argument("--compare", type=Path)
    p.add_argument("--pdf", type=Path, default=ROOT.parent / "data/samples/RC_Coeur_Herault_2024.pdf")
    p.add_argument("--output", type=Path, default=ROOT / "reports/field_metrics.json")
    args = p.parse_args()
    if not args.pdf.is_file():
        p.error("PDF source absent. Téléchargez le RC original indiqué dans eval/README.md.")
    cases = [json.loads(line) for line in (ROOT / "gold_rc.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    checks = json.loads((ROOT / "field_checks.json").read_text(encoding="utf-8"))["checks"]
    if len(cases) != len(checks) or set(checks) != {c["id"] for c in cases}:
        raise ValueError("Les contrôles du gold set ne correspondent pas aux 20 cas.")
    data = args.pdf.read_bytes()
    pages = extract_pages(data, args.pdf.name)
    check_reference(cases, data, pages)
    def run(path):
        prediction = json.loads(path.read_text(encoding="utf-8-sig"))
        return {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                **score(cases, checks, prediction, pages)}
    result = {"gold_set": "RC Cœur d'Hérault 2024, 20 cas, validation indépendante en attente",
              "source_pdf_sha256": hashlib.sha256(data).hexdigest(),
              "historical_structured_baseline": run(args.prediction),
              "prompt_only_baseline": run(args.compare) if args.compare and args.compare.exists() else None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for label in ("historical_structured_baseline", "prompt_only_baseline"):
        item = result[label]
        print(f"{label}: " + ("NOT RUN (no output file supplied)" if item is None else
              f"{item['field_correct_and_source_supported']['correct']}/20 field+source; "
              f"{item['deadline_exact_match']['correct']}/1 exact deadline; "
              f"CI {item['field_correct_and_source_supported']['wilson_95']}"))
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
