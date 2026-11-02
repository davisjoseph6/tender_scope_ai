import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from core.llm import Answer, LLMError, answer_question, extract_requirements, request_structured, match_quote, rate_limit_error


PAGES = [{"document": "RC.pdf", "page": 1, "text": "Certification ISO 27001 obligatoire."}]


def fake_client(payload, finish="stop"):
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        finish_reason=finish, message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
    )])
    return client


def requirement(quote="ISO 27001", source="s1"):
    return {"requirements": [{"category": "certifications", "summary": "Certification demandée", "mandatory": "Oui",
                              "citations": [{"source_id": source, "quote": quote}]}]}


class LLMTests(unittest.TestCase):
    def test_rate_limit_honors_provider_delay_and_safe_fallback(self):
        for value, expected, known in [("125", 125, True), ("bad", 60, False), ("-2", 60, False)]:
            error = RuntimeError("private")
            error.response = SimpleNamespace(headers={"retry-after": value})
            parsed = rate_limit_error(error)
            self.assertEqual(parsed.retry_after, expected)
            self.assertEqual(parsed.known, known)
        error.response.headers = {"retry-after": "Thu, 01 Jan 1970 00:02:00 GMT"}
        with patch("core.llm.time.time", return_value=100):
            self.assertEqual(rate_limit_error(error).retry_after, 20)

    def test_json_validation_failure_is_retried_but_other_400_is_not(self):
        client = fake_client({"requirements": []})
        normal = client.chat.completions.create.return_value
        error = RuntimeError("private generation")
        error.status_code = 400
        error.body = {"error": {"code": "json_validate_failed", "failed_generation": "private"}}
        client.chat.completions.create.side_effect = [error, normal]
        result = extract_requirements(PAGES, client=client)
        self.assertEqual(result["requirements"], [])
        self.assertEqual(client.chat.completions.create.call_count, 2)
        other = fake_client({})
        error.body = {"error": {"code": "unsupported_parameter"}}
        other.chat.completions.create.side_effect = error
        with self.assertRaisesRegex(LLMError, "paramètres"):
            extract_requirements(PAGES, client=other)
        other.chat.completions.create.assert_called_once()

    def test_category_code_is_rendered_in_french(self):
        payload = requirement()
        payload["requirements"][0]["category"] = "technical"
        result = extract_requirements(PAGES, client=fake_client(payload))
        self.assertEqual(result["requirements"][0]["category"], "Prestations techniques")

    def test_interrupted_extraction_resumes_completed_batches(self):
        pages = [{"document": "RC.pdf", "page": i, "text": "ISO 27001"} for i in range(3)]
        client = fake_client({"requirements": []})
        normal = client.chat.completions.create.return_value
        error = RuntimeError("private detail")
        error.status_code = 429
        client.chat.completions.create.side_effect = [normal, error]
        checkpoints = []
        with self.assertRaises(LLMError):
            extract_requirements(pages, client=client, on_progress=checkpoints.append)
        self.assertEqual(checkpoints[-1]["next_chunk"], 2)
        resumed = fake_client({"requirements": []})
        result = extract_requirements(pages, client=resumed, checkpoint=checkpoints[-1])
        self.assertEqual(result["chunks_processed"], 3)
        resumed.chat.completions.create.assert_called_once()
        sent = json.loads(resumed.chat.completions.create.call_args.kwargs["messages"][1]["content"])["sources"]
        self.assertEqual([c["page"] for c in sent], [2])
        # Un autre contenu invalide le point de reprise.
        other = fake_client({"requirements": []})
        extract_requirements(pages + [{"document": "RC.pdf", "page": 4, "text": "DC1"}], client=other, checkpoint=checkpoints[-1])
        self.assertEqual(other.chat.completions.create.call_count, 2)

    def test_whitespace_variations_restore_original_source(self):
        source = "Une certification ISO\n27001\u00a0\u00a0obligatoire est demandée."
        self.assertEqual(match_quote("ISO 27001 obligatoire", source), "ISO\n27001\u00a0\u00a0obligatoire")
        for quote in ["ISO 9001 obligatoire", "ISO 27001 non obligatoire", "iso 27001 obligatoire", ""]:
            self.assertIsNone(match_quote(quote, source))
        self.assertIsNone(match_quote("100", "Seuil : 1000 euros"))

    def test_mixed_extraction_keeps_only_valid_requirements(self):
        payload = requirement()
        payload["requirements"].extend(requirement("ISO 9001")["requirements"])
        result = extract_requirements(PAGES, client=fake_client(payload))
        self.assertEqual(len(result["requirements"]), 1)
        self.assertEqual(result["rejected_requirements"], 1)

    def test_extraction_is_structured_and_grounded(self):
        client = fake_client(requirement())
        result = extract_requirements(PAGES, client=client)
        self.assertEqual(result["requirements"][0]["citations"][0]["document"], "RC.pdf")
        self.assertTrue(result["human_review_required"])
        sent = client.chat.completions.create.call_args.kwargs
        self.assertTrue(sent["response_format"]["json_schema"]["strict"])
        self.assertIn("ISO 27001", sent["messages"][1]["content"])

    def test_fabricated_and_wrong_source_citations_are_rejected(self):
        for payload in [requirement("ISO 9001"), requirement(source="inconnue"), requirement(quote="")]:
            with self.assertRaises(LLMError):
                extract_requirements(PAGES, client=fake_client(payload))

    def test_no_citation_or_invalid_schema_is_rejected(self):
        payload = requirement()
        payload["requirements"][0]["citations"] = []
        for value in [payload, {"unexpected": True}]:
            with self.assertRaises(LLMError):
                extract_requirements(PAGES, client=fake_client(value))

    def test_empty_and_oversized_inputs_never_call_api(self):
        client = MagicMock()
        for pages in [[], [{"document": "RC", "page": 1, "text": "a" * 260000}]]:
            with self.assertRaises(LLMError):
                extract_requirements(pages, client=client)
        client.chat.completions.create.assert_not_called()

    def test_missing_key_and_provider_errors_do_not_leak_details(self):
        with patch("core.llm.settings", return_value={"api_key": "", "model": "test"}):
            with self.assertRaisesRegex(LLMError, "Clé Groq absente"):
                extract_requirements(PAGES)
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("secret-provider-detail")
        with self.assertRaises(LLMError) as error:
            extract_requirements(PAGES, client=client)
        self.assertNotIn("secret-provider-detail", str(error.exception))

    def test_truncated_answer_is_rejected(self):
        with self.assertRaisesRegex(LLMError, "incomplète"):
            extract_requirements(PAGES, client=fake_client(requirement(), "length"))

    def test_truncated_batch_is_split_without_losing_sources(self):
        client = fake_client({"requirements": []})
        normal = client.chat.completions.create.return_value
        truncated = fake_client({}, "length").chat.completions.create.return_value
        client.chat.completions.create.side_effect = [truncated, normal, normal]
        pages = PAGES + [{"document": "RC.pdf", "page": 2, "text": "Seuil de chiffre d’affaires"}]
        result = extract_requirements(pages, client=client)
        self.assertEqual(result["chunks_processed"], 2)
        self.assertEqual(client.chat.completions.create.call_count, 3)
        calls = client.chat.completions.create.call_args_list
        sent = [json.loads(call.kwargs["messages"][1]["content"])["sources"] for call in calls]
        self.assertEqual([len(s) for s in sent], [2, 1, 1])
        self.assertEqual(sent[1] + sent[2], sent[0])

    def test_single_chunk_retry_is_bounded(self):
        client = fake_client({}, "length")
        with self.assertRaises(LLMError):
            extract_requirements(PAGES, client=client)
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertEqual([call.kwargs["max_completion_tokens"] for call in client.chat.completions.create.call_args_list], [6000, 12000])

    def test_rate_limit_has_actionable_message(self):
        client = MagicMock()
        error = RuntimeError("private-provider-detail")
        error.status_code = 429
        client.chat.completions.create.side_effect = error
        with self.assertRaisesRegex(LLMError, "quota Groq atteint"):
            extract_requirements(PAGES, client=client)

    def test_rag_answer_and_no_match_without_call(self):
        client = fake_client({"status": "Réponse sourcée", "answer": "ISO 27001 est demandée.", "citations": [{"source_id": "s1", "quote": "ISO 27001 obligatoire"}]})
        result = answer_question(PAGES, "ISO 27001", client=client)
        self.assertEqual(result["citations"][0]["page"], 1)
        client.reset_mock()
        result = answer_question(PAGES, "garantie bancaire", client=client)
        self.assertEqual(result["status"], "Information insuffisante")
        client.chat.completions.create.assert_not_called()

    def test_uncertain_answer_does_not_display_unsupported_model_text(self):
        client = fake_client({"status": "Information insuffisante", "answer": "Texte non vérifié", "citations": []})
        result = answer_question(PAGES, "ISO", client=client)
        self.assertNotIn("Texte non vérifié", result["answer"])

    def test_every_batch_is_processed_and_cross_batch_source_rejected(self):
        pages = [{"document": "RC.pdf", "page": n, "text": "ISO 27001"} for n in range(1, 10)]
        client = fake_client({"requirements": []})
        result = extract_requirements(pages, client=client)
        self.assertEqual(result["chunks_processed"], 9)
        self.assertEqual(client.chat.completions.create.call_count, 5)
        client = fake_client(requirement())
        result = extract_requirements(pages, client=client)
        self.assertEqual(result["rejected_requirements"], 4)
        self.assertEqual(len(result["requirements"]), 1)
