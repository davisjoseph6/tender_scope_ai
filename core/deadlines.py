"""Conservative date candidates: evidence, not authoritative procurement deadlines."""
import re
from datetime import date
from core.doc_types import normalize

TRIGGER = re.compile(r"date\s+limite|date\s+et\s+heure\s+limites?|remise\s+des\s+offres|reception\s+des\s+offres|depot\s+des\s+offres")
DATE = re.compile(r"(?<!\d)(?:([0-3]?\d)[/-]([01]?\d)[/-]((?:19|20)\d{2})|(\d{1,2})(?:er)?\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre)\s+((?:19|20)\d{2}))(?!\d)", re.I)
TIME = re.compile(r"(?:a\s+|\b)([01]?\d|2[0-3])\s*(?:h|:)\s*([0-5]\d)?\b", re.I)
MONTHS = {month: index for index, month in enumerate("janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre".split(), 1)}


def deadline_candidates(pages: list[dict]) -> dict:
    """Return page-bound exact snippets. Differences are review flags, not legal findings."""
    candidates = []
    for page in pages:
        lines = page["text"].splitlines()
        for index, line in enumerate(lines):
            # Many RC PDFs put the field label and the value on separate lines.
            context = "\n".join(lines[max(0, index - 1):min(len(lines), index + 2)])
            if not TRIGGER.search(normalize(context)):
                continue
            for match in DATE.finditer(normalize(line)):
                if match.group(1):
                    day, month, year = map(int, match.group(1, 2, 3))
                else:
                    day = int(match.group(4))
                    month = MONTHS[match.group(5).lower()]
                    year = int(match.group(6))
                try:
                    value = date(year, month, day).isoformat()
                except ValueError:
                    continue
                clock = TIME.search(normalize(line[match.end():]))
                hour = (f"{int(clock.group(1)):02d}:{int(clock.group(2) or '0'):02d}" if clock else None)
                quote = context.strip()
                result = {"document": page["document"], "page": page["page"], "date": value,
                          "time": hour, "quote": quote}
                if result not in candidates:
                    candidates.append(result)
    values = {(c["date"], c["time"]) for c in candidates}
    return {"candidates": candidates, "requires_review": len(values) != 1,
            "warning": ("Plusieurs dates/heures candidates : vérifier les versions et avenants." if len(values) > 1
                        else "Aucune date limite trouvée : consulter les pièces officielles." if not values
                        else "Date candidate à confirmer dans la dernière version des pièces officielles.")}
