import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class NavigationTests(unittest.TestCase):
    def test_cooldown_blocks_groq_without_discarding_partial_result(self):
        from core.llm import RateLimitError
        with patch("ui.ai_controls.settings", return_value={"api_key": "test", "model": "test"}), patch("ui.page_points_cles.extract_requirements", side_effect=RateLimitError(120, True)) as call:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            app.session_state["pages"] = [{"document": "RC.pdf", "page": 1, "text": "ISO"}]
            app.session_state["ai_checkpoint"] = {"next_chunk": 4, "total_chunks": 12, "findings": [], "rejected": 0}
            app.sidebar.radio[0].set_value("Analyse intelligente").run()
            next(r for r in app.radio if r.label == "Moteur d’extraction").set_value("Groq · IA").run()
            app.checkbox[0].check().run()
            next(b for b in app.button if b.label == "Extraire les exigences avec Groq").click().run()
            self.assertFalse(app.exception)
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(next(b for b in app.button if b.label == "Extraire les exigences avec Groq").disabled)
            self.assertEqual(app.session_state["ai_checkpoint"]["next_chunk"], 4)
            call.assert_called_once()

    def test_groq_requires_explicit_click_and_keeps_result_on_navigation(self):
        result = {"requirements": [], "model": "test-model", "chunks_processed": 1, "pages_without_text": 0}
        with patch("ui.ai_controls.settings", return_value={"api_key": "test-not-a-real-key", "model": "test-model"}), patch("ui.page_points_cles.extract_requirements", return_value=result) as call:
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            app.session_state["pages"] = [{"document": "RC.pdf", "page": 1, "text": "ISO 27001"}]
            app.sidebar.radio[0].set_value("Analyse intelligente").run()
            next(r for r in app.radio if r.label == "Moteur d’extraction").set_value("Groq · IA").run()
            self.assertFalse(app.exception)
            button = next(b for b in app.button if b.label == "Extraire les exigences avec Groq")
            self.assertTrue(button.disabled)
            call.assert_not_called()
            app.checkbox[0].check().run()
            call.assert_not_called()
            next(b for b in app.button if b.label == "Extraire les exigences avec Groq").click().run()
            self.assertFalse(app.exception)
            call.assert_called_once()
            self.assertEqual(app.session_state["ai_extraction"]["model"], "test-model")
            app.sidebar.radio[0].set_value("Tableau de bord").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["ai_extraction"]["model"], "test-model")

    def test_history_does_not_mix_ai_results_between_dossiers(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        pages = [{"document": "RC.pdf", "page": 1, "text": "ISO 27001"}]
        base = {"pages": pages, "documents": [(0, "RC.pdf", pages)], "requirements": [], "review_complete": False}
        first = {**base, "dossier_name": "Premier", "ai_extraction": {"marker": "premier"}, "ai_answer": None}
        second = {**base, "dossier_name": "Second", "ai_extraction": None, "ai_answer": None}
        app.session_state["dossiers"] = {"first": first, "second": second}
        app.session_state["active_dossier"] = "second"
        for key, value in second.items():
            app.session_state[key] = value
        app.sidebar.radio[0].set_value("Mes appels d’offres").run()
        self.assertFalse(app.exception)
        next(s for s in app.selectbox if s.label == "Dossier à ouvrir").set_value("first").run()
        next(b for b in app.button if b.label == "Ouvrir ce dossier").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["ai_extraction"]["marker"], "premier")
        next(s for s in app.selectbox if s.label == "Dossier à ouvrir").set_value("second").run()
        next(b for b in app.button if b.label == "Ouvrir ce dossier").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(app.session_state["ai_extraction"])

    def test_old_navigation_is_migrated(self):
        path = str(Path(__file__).resolve().parents[1] / "app.py")
        for old, expected in [("Dossier", "Mes appels d’offres"), ("Points clés", "Analyse intelligente"), ("Décision", "Décision Bid/No-Bid"), ("inconnue", "Tableau de bord")]:
            app = AppTest.from_file(path)
            app.session_state["navigation"] = old
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.sidebar.radio[0].value, expected)

    def test_six_spaces_and_persistent_decision(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(app.exception)
        pages = [{"document": "RC.pdf", "page": 1, "text": "Date limite : 12 novembre 2026\nCertification ISO 27001"}]
        app.session_state["pages"] = pages
        app.session_state["documents"] = [(0, "RC.pdf", pages)]
        app.session_state["active_dossier"] = "test"
        app.session_state["dossier_name"] = "Marché test"
        app.session_state["requirements"] = [{"label": "ISO", "source": "RC p1", "mandatory": True, "status": "Satisfait"}]
        app.session_state["review_complete"] = True
        for page in ["Décision Bid/No-Bid", "Tableau de bord", "Mes appels d’offres", "Analyse intelligente", "Profil entreprise", "Assistant IA", "Décision Bid/No-Bid"]:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception, page)
        self.assertTrue(app.session_state["review_complete"])
        self.assertTrue(any("Go —" in item.value for item in app.success))
        app.sidebar.radio[0].set_value("Assistant IA").run()
        app.text_input[0].set_value("ISO 27001").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Certification ISO" in item.value for item in app.text))
