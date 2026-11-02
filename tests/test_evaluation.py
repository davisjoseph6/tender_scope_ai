from copy import deepcopy
import json
from pathlib import Path
import unittest

from eval.evaluate import check_reference, evaluate


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.pages = [{"document": "RC.pdf", "page": 1, "text": "Aucun surcoût. Date limite 12 novembre."}]
        self.case = {"id": "q1", "topic": "Surcoût", "document": "RC.pdf", "expected": "Pas de surcoût",
                     "accepted_categories": ["Clauses sensibles"], "sources": [{"page": 1, "quote": "Aucun surcoût.", "anchor": "Aucun surcoût"}],
                     "forbidden_summary_patterns": [["peut entraîner un surcoût", "Sens inversé"]]}
        self.prediction = {"requirements": [{"category": "Clauses sensibles", "summary": "Peut entraîner un surcoût", "mandatory": "Oui",
                                            "citations": [{"document": "RC.pdf", "page": 1, "quote": "Aucun surcoût."}]}]}

    def test_existing_citation_does_not_validate_inverted_summary(self):
        report = evaluate([self.case], self.prediction, self.pages)
        self.assertEqual(report["citation_existence_rate"], 1)
        self.assertEqual(report["source_coverage"], 1)
        self.assertIn("Sens inversé", report["cases"][0]["issues"][0])
        self.assertEqual(report["human_validated_cases"], 0)

    def test_fabricated_or_wrong_page_citation_does_not_count_as_coverage(self):
        for updates in [{"quote": "Aucun surcoût imaginé."}, {"page": 2}, {"document": "autre.pdf"}]:
            prediction = deepcopy(self.prediction)
            prediction["requirements"][0]["citations"][0].update(updates)
            report = evaluate([self.case], prediction, self.pages)
            self.assertEqual(report["cases_with_source_match"], 0)
            self.assertEqual(report["citations_found"], 0)

    def test_empty_export_has_no_citation_rate(self):
        report = evaluate([self.case], {"requirements": []}, self.pages)
        self.assertEqual(report["source_coverage"], 0)
        self.assertIsNone(report["citation_existence_rate"])

    def test_pdf_version_mismatch_rejected(self):
        self.case["pdf_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "version"):
            check_reference([self.case], b"other version", self.pages)

    def test_local_reference_is_bound_to_pdf_and_detects_known_regression(self):
        root = Path(__file__).resolve().parents[1]
        pdf = root / "data/samples/RC_Coeur_Herault_2024.pdf"
        if not pdf.exists():
            self.skipTest("PDF public local absent ; lien de téléchargement dans eval/README.md")
        from core.pdf_reader import extract_pages
        cases = [json.loads(line) for line in (root / "eval/gold_rc.jsonl").read_text(encoding="utf-8").splitlines()]
        pages = extract_pages(pdf.read_bytes(), pdf.name)
        check_reference(cases, pdf.read_bytes(), pages)
        prediction = json.loads((root / "eval/baseline_rc.json").read_text(encoding="utf-8-sig"))
        report = evaluate(cases, prediction, pages)
        inversion = next(c for c in report["cases"] if c["id"] == "rc17")
        self.assertTrue(any("Sens inversé" in issue for issue in inversion["issues"]))
        for case_id in ("rc13", "rc14", "rc15"):
            self.assertFalse(next(c for c in report["cases"] if c["id"] == case_id)["candidate_indices"])
