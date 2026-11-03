import unittest
from core.llm import Extraction
from core.ollama_extraction import extract_requirements_ollama


class OllamaExtractionTests(unittest.TestCase):
    def setUp(self):
        self.pages = [{"document": "RC.txt", "page": 1,
                       "text": "Date limite de remise : 18 décembre 2026 à 12 h."}]

    def test_local_extraction_preserves_source(self):
        def fake(schema, system, task, chunks):
            self.assertEqual(chunks[0]["document"], "RC.txt")
            self.assertIn("COPIE", task)
            return Extraction.model_validate({"requirements": [
                {"category": "deadline", "summary": "Date limite : 18 décembre 2026 à 12 h.",
                 "mandatory": "Oui", "citations": [
                     {"source_id": chunks[0]["id"], "quote": "18 décembre 2026 à 12 h"}
                 ]}
            ]})
        output = extract_requirements_ollama(self.pages, generator=fake)
        self.assertEqual(len(output["requirements"]), 1)
        self.assertEqual(output["requirements"][0]["citations"][0]["page"], 1)

    def test_rejects_hallucinated_citation(self):
        def fake(schema, system, task, chunks):
            return Extraction.model_validate({"requirements": [
                {"category": "deadline", "summary": "Fausse date", "mandatory": "Oui",
                 "citations": [{"source_id": chunks[0]["id"], "quote": "18 janvier 2099"}]}
            ]})
        output = extract_requirements_ollama(self.pages, generator=fake)
        self.assertEqual(output["requirements"], [])
        self.assertEqual(output["rejected_requirements"], 1)

    def test_resumes_after_first_chunk(self):
        pages = self.pages + [{"document": "CCTP.txt", "page": 1, "text": "Maintenance informatique"}]
        checkpoints = []
        count = 0
        def partial(schema, system, task, chunks):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("service interrupted")
            return Extraction(requirements=[])
        with self.assertRaises(RuntimeError):
            extract_requirements_ollama(pages, generator=partial, on_progress=checkpoints.append)
        self.assertEqual(checkpoints[-1]["next_chunk"], 1)
        second_calls = []
        def resume(schema, system, task, chunks):
            second_calls.append(chunks[0]["document"])
            return Extraction(requirements=[])
        result = extract_requirements_ollama(pages, checkpoint=checkpoints[-1], generator=resume)
        self.assertEqual(result["chunks_processed"], 2)
        self.assertEqual(second_calls, ["CCTP.txt"])
