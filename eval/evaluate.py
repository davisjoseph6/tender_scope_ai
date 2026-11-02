"""python -m eval.evaluate --prediction eval/baseline_rc.json --pdf data/samples/RC_Coeur_Herault_2024.pdf"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from core.pdf_reader import extract_pages


def compact(text):
    return " ".join(text.split())


def check_reference(cases, pdf_bytes, pages):
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    for case in cases:
        if case["pdf_sha256"] != digest:
            raise ValueError("Le PDF ne correspond pas à la version annotée.")
        for source in case["sources"]:
            page = pages[source["page"] - 1]
            if source["quote"] not in page["text"] or compact(source["anchor"]) not in compact(source["quote"]):
                raise ValueError(f"Source de référence invalide : {case['id']}")


def evaluate(cases, prediction, pages):
    by_page = {(p["document"], p["page"]): p["text"] for p in pages}
    requirements = prediction["requirements"]
    valid_citations = 0
    total_citations = 0
    for item in requirements:
        for citation in item.get("citations", []):
            total_citations += 1
            source = by_page.get((citation["document"], citation["page"]), "")
            valid_citations += bool(citation["quote"].strip()) and citation["quote"] in source
    rows = []
    for case in cases:
        matched = []
        for index, item in enumerate(requirements):
            if any(c["document"] == case["document"] and c["page"] == s["page"]
                   and compact(s["anchor"]) in compact(c["quote"])
                   and bool(c["quote"].strip()) and c["quote"] in by_page.get((c["document"], c["page"]), "")
                   for s in case["sources"] for c in item.get("citations", [])):
                matched.append(index)
        issues = []
        if not matched:
            issues.append("Passage attendu non retrouvé dans les citations de l’export")
        selected = [requirements[i] for i in matched]
        if selected and not any(item["category"] in case["accepted_categories"] for item in selected):
            issues.append("Catégorie à revoir")
        # Contrôles spécifiques au cas ; pas de juge sémantique général.
        for index in matched:
            summary = requirements[index]["summary"]
            for pattern, reason in case.get("forbidden_summary_patterns", []):
                if re.search(pattern, summary, re.IGNORECASE):
                    issues.append(f"Élément {index + 1} : {reason}")
            for pattern, reason in case.get("required_summary_patterns", []):
                if not re.search(pattern, summary, re.IGNORECASE):
                    issues.append(f"Élément {index + 1} : {reason}")
            if case.get("conditional") and requirements[index].get("mandatory") == "Oui":
                issues.append(f"Élément {index + 1} : condition présente ; le champ obligatoire=Oui ne distingue pas son applicabilité")
        rows.append({"id": case["id"], "topic": case["topic"], "expected": case["expected"],
                     "candidate_indices": [i + 1 for i in matched], "issues": issues,
                     "human_review": "À relire", "sources": case["sources"]})
    covered = sum(bool(row["candidate_indices"]) for row in rows)
    return {"prediction_items": len(requirements), "reference_cases": len(cases), "cases_with_source_match": covered,
            "source_coverage": covered / len(cases) if cases else None,
            "citations_found": valid_citations, "citations_total": total_citations,
            "citation_existence_rate": valid_citations / total_citations if total_citations else None,
            "cases_flagged": sum(bool(row["issues"]) for row in rows),
            "human_validated_cases": 0,
            "limitations": "Couverture de passages par ancrages exacts et alertes ciblées. Ni rappel exhaustif des exigences, ni exactitude sémantique, ni taux de faux éligibles. Référence initiale à valider par l’équipe ; un seul marché.",
            "cases": rows}


def markdown_report(report):
    lines = ["# Évaluation initiale — RC Cœur d’Hérault 2024", "",
             f"- Éléments dans l’export : {report['prediction_items']}",
             f"- Cas avec passage source cité : {report['cases_with_source_match']}/{report['reference_cases']}",
             f"- Citations présentes sur la page annoncée : {report['citations_found']}/{report['citations_total']}",
             f"- Cas signalés pour relecture : {report['cases_flagged']}", "", report["limitations"], "",
             "La présence d’une citation ne valide pas le sens du résumé. Un cas sans correspondance peut nécessiter une recherche manuelle dans l’export.", ""]
    for row in report["cases"]:
        lines += [f"## {row['id']} — {row['topic']}", "", "Attendu : " + row["expected"], "",
                  "Éléments candidats (numéros à partir de 1) : " + (", ".join(map(str, row["candidate_indices"])) or "aucun"), "",
                  "Contrôle : " + (" ; ".join(row["issues"]) or "Aucune alerte automatique ; sens à relire."), "",
                  "Validation humaine : À relire", ""]
    return "\n".join(lines)


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Évaluation locale sans appel API")
    parser.add_argument("--prediction", type=Path, default=root / "baseline_rc.json")
    parser.add_argument("--gold", type=Path, default=root / "gold_rc.jsonl")
    parser.add_argument("--pdf", type=Path, default=root.parent / "data/samples/RC_Coeur_Herault_2024.pdf")
    parser.add_argument("--output", type=Path, default=root / "reports/baseline")
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()]
    data = args.pdf.read_bytes()
    pages = extract_pages(data, args.pdf.name)
    check_reference(cases, data, pages)
    result = evaluate(cases, json.loads(args.prediction.read_text(encoding="utf-8-sig")), pages)
    result["pdf_sha256"] = hashlib.sha256(data).hexdigest()
    result["prediction_sha256"] = hashlib.sha256(args.prediction.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown_report(result), encoding="utf-8")
    print(f"Sources citées : {result['cases_with_source_match']}/{result['reference_cases']} cas ; citations vérifiées : {result['citations_found']}/{result['citations_total']} ; cas signalés : {result['cases_flagged']}")


if __name__ == "__main__":
    main()
