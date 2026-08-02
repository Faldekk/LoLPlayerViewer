"""Bezpieczne odczytywanie lokalnej konfiguracji spoza repozytorium."""

import json
import os
from pathlib import Path
import sys


CONFIG_PATH = (
    Path(sys.executable).resolve().parent / "config.json"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent / "config.json"
)

DEFAULT_PROXY_URL = "https://lol-player-viewer-proxy.01199206.workers.dev"


def _load_config() -> dict:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_api_key() -> str:
    key = _load_config().get("riot_api_key", "")
    return key.strip() if isinstance(key, str) else ""


def load_proxy_url() -> str:
    configured = _load_config().get("riot_proxy_url", "")
    value = os.environ.get("LOL_PLAYER_VIEWER_PROXY_URL", "") or configured or DEFAULT_PROXY_URL
    return value.strip().rstrip("/") if isinstance(value, str) else ""
