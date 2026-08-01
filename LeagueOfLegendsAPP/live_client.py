"""Odczyt statystyk z lokalnego klienta gry League of Legends."""

import json
import ssl
import urllib.error
import urllib.request


class LiveClient:
    URL = "https://127.0.0.1:2999/liveclientdata/allgamedata"

    @classmethod
    def load(cls) -> dict | None:
        """Zwraca dane bieżącej gry; None oznacza, że lokalna gra nie działa."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        request = urllib.request.Request(
            cls.URL, headers={"User-Agent": "LoL-Player-Viewer/1.0"}
        )
        try:
            with urllib.request.urlopen(
                request, timeout=2, context=context
            ) as response:
                payload = json.load(response)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        active = payload.get("activePlayer", {})
        game = payload.get("gameData", {})
        return {
            "game_time": max(0, int(game.get("gameTime", 0) or 0)),
            "game_mode": game.get("gameMode", ""),
            "active_riot_id": active.get("riotId")
            or active.get("summonerName", ""),
            "current_gold": int(active.get("currentGold", 0) or 0),
            "players": [cls._player(item) for item in payload.get("allPlayers", [])],
        }

    @staticmethod
    def _player(player: dict) -> dict:
        scores = player.get("scores", {})
        return {
            "riot_id": player.get("riotId")
            or player.get("summonerName")
            or "Gracz",
            "champion": player.get("championName", "?"),
            "team": player.get("team", ""),
            "position": player.get("position", ""),
            "level": int(player.get("level", 0) or 0),
            "kills": int(scores.get("kills", 0) or 0),
            "deaths": int(scores.get("deaths", 0) or 0),
            "assists": int(scores.get("assists", 0) or 0),
            "cs": int(scores.get("creepScore", 0) or 0),
            "vision": int(scores.get("wardScore", 0) or 0),
            "is_dead": bool(player.get("isDead", False)),
            "respawn": max(0, int(player.get("respawnTimer", 0) or 0)),
            "items": [
                int(item.get("itemID", 0) or 0)
                for item in player.get("items", [])
                if int(item.get("itemID", 0) or 0) > 0
            ],
        }
