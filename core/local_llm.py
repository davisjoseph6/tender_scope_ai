"""Local Ollama structured generation; no automatic network request from the UI."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from pydantic import ValidationError
from core.hybrid import ollama_url


class LocalModelError(ValueError):
    pass


def request_local_json(schema, system: str, task: str, chunks: list[dict], *,
                       model: str | None = None, opener=urlopen):
    payload = {
        "model": model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        "stream": False, "format": schema.model_json_schema(),
        "options": {"temperature": 0},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps({"task": task, "sources": chunks}, ensure_ascii=False)}],
    }
    request = Request(ollama_url() + "/api/chat",
                      data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with opener(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
        return schema.model_validate_json(data["message"]["content"])
    except (URLError, HTTPError, OSError, KeyError, TypeError, ValueError, ValidationError):
        raise LocalModelError("Réponse Ollama indisponible ou invalide. Vérifiez le service local, le modèle et le JSON structuré.") from None
