import ast
import io
from pathlib import Path
import unittest

from pypdf import PdfWriter

from core.pdf_reader import extract_pages


class PdfReaderTests(unittest.TestCase):
    def test_blank_pages_keep_source_and_page_numbers(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO()
        writer.write(buffer)
        self.assertEqual(extract_pages(buffer.getvalue(), "scan.pdf"), [
            {"document": "scan.pdf", "page": 1, "text": ""},
            {"document": "scan.pdf", "page": 2, "text": ""},
        ])

    def test_password_protected_pdf_is_rejected(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("secret")
        buffer = io.BytesIO()
        writer.write(buffer)
        with self.assertRaises(ValueError):
            extract_pages(buffer.getvalue(), "protected.pdf")

    def test_core_does_not_import_ui_or_streamlit(self):
        root = Path(__file__).resolve().parents[1] / "core"
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                self.assertFalse(any(n.split(".")[0] in {"streamlit", "ui"} for n in names), path)
