import unittest
from core.deadlines import deadline_candidates
from core.hybrid import similarity, retrieve_hybrid
from core.rag import chunk_pages


class DemoTests(unittest.TestCase):
    def test_detects_two_candidate_deadlines_without_selecting_an_authority(self):
        pages = [
            {"document": "RC.pdf", "page": 1, "text": "Date limite de remise des offres : 15 décembre 2026 à 12 h 00."},
            {"document": "Rectificatif.pdf", "page": 2, "text": "La date limite de remise des offres est reportée au 18 décembre 2026 à 12 h 00."},
        ]
        result = deadline_candidates(pages)
        self.assertTrue(result["requires_review"])
        self.assertIn("2026-12-15", [c["date"] for c in result["candidates"]])
        self.assertIn("2026-12-18", [c["date"] for c in result["candidates"]])
        self.assertTrue(all(c["quote"] in pages[i]["text"] for i, c in enumerate(result["candidates"][:2])))

    def test_invalid_dates_dont_become_deadlines(self):
        self.assertEqual(deadline_candidates([{"document": "RC", "page": 1,
            "text": "Date limite : 33 décembre 2026"}])["candidates"], [])

    def test_hybrid_keeps_provenance_and_ranks_semantic_signal(self):
        chunks = chunk_pages([
            {"document": "A", "page": 1, "text": "conditions techniques"},
            {"document": "B", "page": 3, "text": "fin des candidatures"},
        ])
        def fake_embeddings(texts):
            return [[1, 0], [0, 1], [1, 0]]
        ranked = retrieve_hybrid(chunks, "échéance de dépôt", embedder=fake_embeddings)
        self.assertEqual(ranked[0]["document"], "B")
        self.assertEqual(ranked[0]["page"], 3)
        self.assertEqual(similarity([0, 0], [1, 0]), 0)
