import io
import json
import unittest
from core.boamp import get_notice, validated_id, BOAMPError, notice_evidence


class FakeResponse:
    def __init__(self, payload):
        self.data = io.BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.data.close()
    def read(self, size=-1):
        return self.data.read(size)


class BOAMPTests(unittest.TestCase):
    def test_only_published_fields_and_no_buyer_portal_fetch(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            return FakeResponse({"results": [{"idweb": "26-106035", "objet": "Services IT",
                "datelimitereponse": "2026-12-02T12:00:00+01:00", "private_field": "exclude"}]})
        row = get_notice("26-106035", opener=opener)
        self.assertEqual(len(calls), 1)
        self.assertIn("select=", calls[0])
        self.assertNotIn("DONNEES", calls[0])
        self.assertTrue(calls[0].startswith("https://boamp-datadila.opendatasoft.com/"))
        self.assertNotIn("private_field", row)
        self.assertEqual(row["source_url"], "https://www.boamp.fr/pages/avis/?q=idweb:26-106035")
        self.assertEqual(next(item for item in notice_evidence(row) if item["field"] == "objet")["value"], "Services IT")

    def test_rectificatif_requires_verification(self):
        row = get_notice("26-106035", opener=lambda *_args, **_kw:
                         FakeResponse({"results": [{"idweb": "26-106035", "etat": "RECTIFICATIF"}]}))
        self.assertTrue(row["requires_verification"])

    def test_no_arbitrary_query_or_url(self):
        for candidate in ["https://evil.example", '26-106035" or 1=1', "../file", "26-xyz"]:
            with self.assertRaises(BOAMPError):
                validated_id(candidate)

    def test_wrong_notice_id_is_rejected(self):
        with self.assertRaises(BOAMPError):
            get_notice("26-106035", opener=lambda *_args, **_kw:
                       FakeResponse({"results": [{"idweb": "26-000000"}]}))


    def test_http_status_is_visible_without_leaking_response_body(self):
        from urllib.error import HTTPError
        from core.boamp import BOAMPError
        def bad(request, timeout):
            raise HTTPError(request.full_url, 503, "secret-provider-internals", {}, None)
        with self.assertRaisesRegex(BOAMPError, "HTTP 503") as cm:
            get_notice("26-99630", opener=bad)
        self.assertNotIn("secret-provider-internals", str(cm.exception))

    def test_offline_example_is_labeled_and_exists(self):
        from pathlib import Path
        file = Path(__file__).resolve().parents[1] / "data/demo/BOAMP_26-99630_snapshot.json"
        record = json.loads(file.read_text(encoding="utf-8"))
        self.assertEqual(record["idweb"], "26-99630")
        self.assertIn("not an API response", record["_snapshot_note"])
