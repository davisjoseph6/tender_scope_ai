import unittest
from eval.field_metrics import score, normalized, wilson

CASE = {"id": "rc01", "topic": "Date", "document": "RC.pdf",
        "accepted_categories": ["Date limite"],
        "sources": [{"page": 1, "anchor": "01/08/2024 à 11 h"}]}
PAGES = [{"document": "RC.pdf", "page": 1, "text": "Date limite : 01/08/2024 à 11 h."}]


class FieldMetricTests(unittest.TestCase):
    def test_quote_without_value_is_not_correct_field(self):
        output = {"requirements": [{"category": "Date limite", "summary": "Date limite de remise",
                  "citations": [{"document": "RC.pdf", "page": 1, "quote": "01/08/2024 à 11 h"}]}]}
        report = score([CASE], {"rc01": ["01/08/2024", "11 h"]}, output, PAGES)
        self.assertEqual(report["source_coverage"]["correct"], 1)
        self.assertEqual(report["field_correct_and_source_supported"]["correct"], 0)
        self.assertEqual(report["deadline_exact_match"]["correct"], 0)

    def test_exact_value_and_quote_count(self):
        output = {"requirements": [{"category": "Date limite", "summary": "01/08/2024 à 11 h",
                  "citations": [{"document": "RC.pdf", "page": 1, "quote": "01/08/2024 à 11 h"}]}]}
        report = score([CASE], {"rc01": ["01/08/2024", "11 h"]}, output, PAGES)
        self.assertEqual(report["field_correct_and_source_supported"]["correct"], 1)

    def test_wrong_page_fails_even_with_correct_value(self):
        output = {"requirements": [{"category": "Date limite", "summary": "01/08/2024 à 11 h",
                  "citations": [{"document": "RC.pdf", "page": 2, "quote": "01/08/2024 à 11 h"}]}]}
        report = score([CASE], {"rc01": ["01/08/2024", "11 h"]}, output, PAGES)
        self.assertEqual(report["field_correct_and_source_supported"]["correct"], 0)

    def test_wilson_is_bounded(self):
        for good in range(21):
            lo, hi = wilson(good, 20)
            self.assertTrue(0 <= lo <= good / 20 + 1e-4 <= hi + 1e-4 <= 1.0001)

    def test_accent_normalization(self):
        self.assertEqual(normalized("RÉSILIATION"), "resiliation")
