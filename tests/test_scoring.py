import unittest

from core.scoring import score_requirements


class ScoringTests(unittest.TestCase):
    def test_empty_checklist_never_gives_go(self):
        self.assertEqual(score_requirements([], review_complete=True)["verdict"], "À vérifier")

    def test_mandatory_failure_blocks(self):
        self.assertEqual(score_requirements([{"mandatory": True, "status": "Non satisfait"}])["verdict"], "No-Go")

    def test_unknown_and_incomplete_review_prevent_go(self):
        for items, complete in [([{"status": "À vérifier"}], True), ([{"status": "Satisfait"}], False)]:
            self.assertEqual(score_requirements(items, review_complete=complete)["verdict"], "À vérifier")

    def test_go_requires_explicit_review(self):
        self.assertEqual(score_requirements([{"mandatory": True, "status": "Satisfait"}], review_complete=True)["verdict"], "Go")

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            score_requirements([{"status": "eligible"}], review_complete=True)
