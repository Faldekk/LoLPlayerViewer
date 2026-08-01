"""Lokalny zapis niesekretnych ustawień użytkownika."""

import json
import os
from pathlib import Path


class FavoritesStore:
    def __init__(self) -> None:
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / ".config"
        self.path = base / "LoLPlayerViewer" / "favorites.json"

    def load(self) -> list[dict[str, str]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        favorites = []
        for item in data:
            if not isinstance(item, dict):
                continue
            riot_id = str(item.get("riot_id", "")).strip()
            region = str(item.get("region", "")).strip()
            if riot_id and region:
                favorites.append({"riot_id": riot_id, "region": region})
        return favorites

    def save(self, favorites: list[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(favorites, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)
