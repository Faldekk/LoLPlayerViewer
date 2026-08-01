"""Bezpieczne odczytywanie lokalnej konfiguracji spoza repozytorium."""

import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def load_api_key() -> str:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    key = payload.get("riot_api_key", "") if isinstance(payload, dict) else ""
    return key.strip() if isinstance(key, str) else ""
