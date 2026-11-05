import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from core.grok import GrokError, request_grok_json, extract_requirements_grok, answer_question_grok
from core.llm import Extraction, Answer


class FakeResponse:
    def __init__(self, payload):
        self.buf = io.BytesIO(json.dumps(payload).encode())
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.buf.close()
    def read(self, size=-1):
        return self.buf.read(size)


def result_payload(data):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps(data, ensure_ascii=False)}
    ]}]}


class GrokTests(unittest.TestCase):
    def test_xai_request_has_schema_store_false_and_no_tools(self):
        calls = []
        def opener(request, timeout):
            calls.append(request)
            return FakeResponse(result_payload({"requirements": []}))
        with patch("core.grok.grok_settings", return_value={"api_key": "secret-test-key", "model": "grok-test"}):
            result = request_grok_json(Extraction, "system", "task", [{"id": "s1", "text": "RC", "page": 1, "document": "RC"}], opener=opener)
        self.assertEqual(result.requirements, [])
        req = calls[0]
        self.assertEqual(req.full_url, "https://api.x.ai/v1/responses")
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], "grok-test")
        self.assertFalse(payload["store"])
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertEqual(payload["input"][0]["role"], "system")

    def test_missing_key_fails_before_external_request(self):
        with patch("core.grok.grok_settings", return_value={"api_key": "", "model": "grok-test"}):
            with self.assertRaisesRegex(GrokError, "XAI_API_KEY"):
                request_grok_json(Extraction, "sys", "task", [{"id": "s1", "text": "Hi"}],
                    opener=lambda *_args, **_kw: self.fail("should not call API"))

    def test_http_auth_error_sanitizes_provider_body(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 401, "secret-key-in-message", {}, None)
        with patch("core.grok.grok_settings", return_value={"api_key": "secret-test-key", "model": "grok-test"}):
            with self.assertRaises(GrokError) as err:
                request_grok_json(Extraction, "sys", "task", [{"id": "s1", "text": "Hi"}], opener=opener)
        self.assertIn("401", str(err.exception))
        self.assertNotIn("secret", str(err.exception))

    def test_non_completed_response_rejected(self):
        with patch("core.grok.grok_settings", return_value={"api_key": "secret-test-key", "model": "grok-test"}):
            with self.assertRaises(GrokError):
                request_grok_json(Extraction, "sys", "task", [{"id": "s1", "text": "Hi"}],
                    opener=lambda *a, **k: FakeResponse({"status":"incomplete", "output":[]}))

    def test_grok_extraction_verifies_quotes_and_progress(self):
        pages = [{"document": "RC.txt", "page": 1, "text": "Date limite : 18 décembre 2026 à 12 h."}]
        saved = []
        def generator(schema, system, task, batch):
            return Extraction.model_validate({"requirements": [
                {"category": "deadline", "summary": "18 décembre 2026 à 12 h", "mandatory": "Oui",
                 "citations": [{"source_id": batch[0]["id"], "quote": "18 décembre 2026 à 12 h"}]},
                {"category": "deadline", "summary": "Date fabriquée", "mandatory": "Oui",
                 "citations": [{"source_id": batch[0]["id"], "quote": "2099"}]}
            ]})
        out = extract_requirements_grok(pages, generator=generator, on_progress=saved.append)
        self.assertEqual(len(out["requirements"]), 1)
        self.assertEqual(out["rejected_requirements"], 1)
        self.assertEqual(saved[0]["next_chunk"], 1)

    def test_answer_requires_valid_source_and_abstains_when_no_match(self):
        pages = [{"document": "RC", "page": 1, "text": "Certification ISO 27001 obligatoire."}]
        def gen(schema, system, task, batch):
            return Answer.model_validate({"status":"Réponse sourcée", "answer":"ISO 27001",
                 "citations":[{"source_id":batch[0]["id"],"quote":"ISO 27001"}]})
        answer = answer_question_grok(pages, "ISO 27001", generator=gen)
        self.assertEqual(answer["citations"][0]["document"], "RC")
        unanswered = answer_question_grok(pages, "garantie bancaire", generator=lambda *a: self.fail("no call"))
        self.assertEqual(unanswered["status"], "Information insuffisante")
