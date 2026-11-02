import unittest

from core.search import search_passages


class SearchTests(unittest.TestCase):
    def test_ranking_and_exact_sources(self):
        pages = [
            {"document": "CCAP.pdf", "page": 4, "text": "Pénalités\nRetard de livraison"},
            {"document": "RC.pdf", "page": 2, "text": "La certification ISO 27001 est demandée."},
        ]
        result = search_passages(pages, "Quelle certification ISO 27001 ?")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["document"], "RC.pdf")
        self.assertEqual(result[0]["page"], 2)
        self.assertIn(result[0]["quote"], pages[1]["text"])

    def test_no_result_is_not_fabricated(self):
        pages = [{"document": "RC.pdf", "page": 1, "text": "Présentation du marché"}]
        self.assertEqual(search_passages(pages, "ISO 9001"), [])
        self.assertEqual(search_passages(pages, "quelle est la"), [])
