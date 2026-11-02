"""Read-only BOAMP OpenDataSoft v2 adapter. Never accesses buyer portals or DCE links."""
import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE = "https://boamp-datadila.opendatasoft.com/api/explore/v2.0/catalog/datasets/boamp/records"
ID_RE = re.compile(r"^\d{2}-\d{4,7}$")
ALLOWED_FIELDS = (
    "idweb", "objet", "nomacheteur", "datelimitereponse", "dateparution",
    "etat", "type_avis", "type_marche", "procedure_libelle", "url_avis",
    "annonce_lie", "annonces_anterieures",
)
SOURCE_URL = "https://www.boamp.fr/pages/avis/?q=idweb:"


class BOAMPError(ValueError):
    pass


def validated_id(idweb: str) -> str:
    candidate = idweb.strip()
    if not ID_RE.fullmatch(candidate):
        raise BOAMPError("Identifiant BOAMP attendu : 26-106035 (année-numéro).")
    return candidate


def notice_from_record(record: dict) -> dict:
    """Retain only explicitly published fields. A missing field is unknown."""
    if not isinstance(record, dict):
        raise BOAMPError("Notice BOAMP invalide.")
    row = {field: record.get(field) for field in ALLOWED_FIELDS}
    identifier = validated_id(str(row["idweb"] or ""))
    row["source_url"] = SOURCE_URL + identifier
    row["source_provider"] = "DILA / BOAMP (OpenDataSoft)"
    row["requires_verification"] = (not bool(row["datelimitereponse"])
        or str(row.get("etat") or "").upper() == "RECTIFICATIF"
        or bool(row.get("annonce_lie")) or bool(row.get("annonces_anterieures")))
    return row


def get_notice(idweb: str, *, opener=urlopen) -> dict:
    """Queries only BOAMP OpenDataSoft, never an arbitrary URL from the notice."""
    identifier = validated_id(idweb)
    params = urlencode({"where": f'idweb="{identifier}"', "limit": 1})
    request = Request(BASE + "?" + params, headers={"Accept": "application/json",
                        "User-Agent": "TenderScopeAI-classroom-prototype/0.5"})
    try:
        with opener(request, timeout=15) as response:
            data = json.loads(response.read(1_000_000).decode("utf-8"))
        rows = data["results"]
        if not isinstance(rows, list):
            raise ValueError("results must be list")
        for row in rows:
            if isinstance(row, dict) and row.get("idweb") == identifier:
                return notice_from_record(row)
    except (HTTPError, URLError, OSError, ValueError, KeyError, UnicodeError) as error:
        raise BOAMPError("Service BOAMP indisponible ou réponse invalide. Réessayez ou utilisez le dossier fictif hors ligne.") from None
    raise BOAMPError("Aucun avis BOAMP correspondant à cet identifiant.")


def notice_evidence(row: dict) -> list[dict]:
    """Each item contains exact API field value and its provenance; no LLM interpretation."""
    evidence = []
    for field in ALLOWED_FIELDS:
        value = row.get(field)
        if value is None or value == "" or value == []:
            continue
        evidence.append({"field": field, "value": value,
                         "provider": row["source_provider"], "idweb": row["idweb"],
                         "url": row["source_url"]})
    return evidence
