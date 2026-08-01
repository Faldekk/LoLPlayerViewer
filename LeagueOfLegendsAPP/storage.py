"""Lokalny zapis niesekretnych ustawień użytkownika."""

import json
import os
from pathlib import Path
from datetime import datetime


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


class LpTrackerStore:
    TIERS = {
        "IRON": 0, "BRONZE": 1, "SILVER": 2, "GOLD": 3,
        "PLATINUM": 4, "EMERALD": 5, "DIAMOND": 6,
        "MASTER": 7, "GRANDMASTER": 7, "CHALLENGER": 7,
    }
    DIVISIONS = {"IV": 0, "III": 1, "II": 2, "I": 3}

    def __init__(self) -> None:
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / ".config"
        self.path = base / "LoLPlayerViewer" / "lp_history.json"

    def _load_all(self) -> dict[str, list[dict]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @classmethod
    def _rank(cls, ranks: list[dict], queue: str) -> dict | None:
        rank = next((item for item in ranks if item.get("queueType") == queue), None)
        if not rank:
            return None
        tier = str(rank.get("tier", "")).upper()
        division = str(rank.get("rank", ""))
        lp = int(rank.get("leaguePoints", 0) or 0)
        score = cls.TIERS.get(tier, 0) * 400 + cls.DIVISIONS.get(division, 0) * 100 + lp
        label = f"{tier.title()} {division} · {lp} LP".replace("  ", " ")
        return {"tier": tier, "rank": division, "lp": lp, "score": score, "label": label}

    def record(self, puuid: str, riot_id: str, region: str, ranks: list[dict]) -> dict:
        data = self._load_all()
        key = f"{region}:{puuid}"
        stored = data.get(key, [])
        history = [item for item in stored if isinstance(item, dict)] if isinstance(stored, list) else []
        snapshot = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "riot_id": riot_id,
            "region": region,
            "solo": self._rank(ranks, "RANKED_SOLO_5x5"),
            "flex": self._rank(ranks, "RANKED_FLEX_SR"),
        }
        previous = history[-1] if history else None
        changed = previous is None or any(
            (previous.get(queue) or {}).get("score") != (snapshot.get(queue) or {}).get("score")
            for queue in ("solo", "flex")
        )
        if changed:
            history.append(snapshot)
            data[key] = history[-200:]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
            history = data[key]
        changes = {}
        for queue in ("solo", "flex"):
            current_rank = snapshot.get(queue)
            prior_rank = previous.get(queue) if previous else None
            changes[queue] = (
                current_rank["score"] - prior_rank["score"]
                if current_rank and prior_rank else None
            )
        return {"history": history, "changes": changes, "recorded": changed}
