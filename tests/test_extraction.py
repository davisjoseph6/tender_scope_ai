import unittest

from core.doc_types import detect_doc_type
from core.extraction import extract_key_info


class ExtractionTests(unittest.TestCase):
    def test_citations_are_exact_and_page_bound(self):
        text = "Candidature\nDate limite : 12 novembre 2026 à 12h\nDépôt électronique"
        found = extract_key_info([{"document": "RC.pdf", "page": 3, "text": text}])
        self.assertEqual(found[0]["category"], "Date limite")
        self.assertEqual(found[0]["page"], 3)
        self.assertEqual(found[0]["document"], "RC.pdf")
        self.assertIn(found[0]["quote"], text)

    def test_missing_information_is_not_invented(self):
        self.assertEqual(extract_key_info([{"document": "RC.pdf", "page": 1, "text": "Présentation du marché"}]), [])

    def test_negation_is_preserved_for_human_review(self):
        text = "La certification ISO 27001 n’est pas obligatoire."
        found = extract_key_info([{"document": "RC.pdf", "page": 1, "text": text}])
        self.assertEqual(found[0]["quote"], text)

    def test_document_detection(self):
        self.assertEqual(detect_doc_type("01_RC.pdf"), "RC")
        self.assertEqual(detect_doc_type("piece.pdf", "CAHIER DES CLAUSES TECHNIQUES PARTICULIÈRES"), "CCTP")
        self.assertEqual(detect_doc_type("inconnu.pdf"), "À vérifier")
