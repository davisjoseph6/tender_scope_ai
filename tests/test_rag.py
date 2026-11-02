import unittest

from core.rag import chunk_pages, retrieve


class RagTests(unittest.TestCase):
    def test_chunks_preserve_full_text_and_page(self):
        text = "a" * 100 + "ISO 27001" + "b" * 100
        chunks = chunk_pages([{"document": "RC.pdf", "page": 8, "text": text}], size=60, overlap=10)
        self.assertEqual(chunks[0]["text"] + "".join(c["text"][10:] for c in chunks[1:]), text)
        self.assertTrue(all(c["document"] == "RC.pdf" and c["page"] == 8 for c in chunks))
        self.assertEqual(len({c["id"] for c in chunks}), len(chunks))

    def test_bm25_finds_source_and_abstains(self):
        chunks = chunk_pages([
            {"document": "RC.pdf", "page": 1, "text": "Certification ISO 27001 obligatoire"},
            {"document": "CCAP.pdf", "page": 2, "text": "Pénalités de retard de livraison"},
        ])
        self.assertEqual(retrieve(chunks, "Quelles pénalités ?")[0]["document"], "CCAP.pdf")
        self.assertEqual(retrieve(chunks, "garantie bancaire"), [])
        self.assertEqual(retrieve(chunks, "quelle est la"), [])

    def test_invalid_chunk_options(self):
        with self.assertRaises(ValueError):
            chunk_pages([], 100, 100)
