"""Klient oficjalnego Riot Games API."""

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from config import QUEUE_NAMES
from models import PlayerData


class RiotApiError(Exception):
    """Czytelny dla użytkownika błąd Riot API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RiotApiClient:
    def __init__(self, api_key: str, platform: str, regional: str) -> None:
        self.api_key = api_key
        self.platform = platform
        self.regional = regional

    def _get(self, host: str, path: str, allow_not_found: bool = False):
        request = urllib.request.Request(
            f"https://{host}.api.riotgames.com{path}",
            headers={"X-Riot-Token": self.api_key, "User-Agent": "LoL-Player-Viewer/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.load(response)
                if not isinstance(data, (dict, list)):
                    raise RiotApiError(
                        f"Endpoint {path.split('?')[0]} zwrócił nieobsługiwany format danych."
                    )
                return data
        except urllib.error.HTTPError as error:
            if error.code == 404 and allow_not_found:
                return None
            messages = {
                400: "Riot API odrzuciło nieprawidłowe dane.",
                401: "Klucz Riot API jest nieprawidłowy lub wygasł.",
                403: "Brak dostępu. Sprawdź klucz Riot API.",
                404: "Nie znaleziono gracza o takim Riot ID w wybranym regionie.",
                429: "Przekroczono limit zapytań. Spróbuj ponownie za chwilę.",
                500: "Riot API ma chwilowy problem. Spróbuj później.",
                503: "Usługa Riot API jest chwilowo niedostępna.",
            }
            raise RiotApiError(
                messages.get(error.code, f"Błąd Riot API (HTTP {error.code})."),
                status_code=error.code,
            ) from error
        except urllib.error.URLError as error:
            raise RiotApiError(
                "Nie można połączyć się z Riot API. Sprawdź internet."
            ) from error
        except TimeoutError as error:
            raise RiotApiError("Riot API nie odpowiedziało na czas.") from error

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    def load_player(
        self, game_name: str, tag_line: str, match_count: int = 30,
        include_live: bool = True,
    ) -> PlayerData:
        account = self._get(
            self.regional,
            "/riot/account/v1/accounts/by-riot-id/"
            f"{self._quote(game_name)}/{self._quote(tag_line)}",
        )
        puuid = account.get("puuid") if isinstance(account, dict) else None
        if not puuid:
            raise RiotApiError("Odpowiedź ACCOUNT-V1 nie zawiera identyfikatora PUUID.")
        summoner = self._get(
            self.platform,
            f"/lol/summoner/v4/summoners/by-puuid/{self._quote(puuid)}",
        )
        ranks = self._get(
            self.platform,
            f"/lol/league/v4/entries/by-puuid/{self._quote(puuid)}",
        )
        match_ids = self._get(
            self.regional,
            f"/lol/match/v5/matches/by-puuid/{self._quote(puuid)}/ids?start=0&count={match_count}",
        )
        matches = []
        for match_id in match_ids:
            raw_match = self._get(
                self.regional, f"/lol/match/v5/matches/{self._quote(match_id)}"
            )
            participant = next(
                (item for item in raw_match["info"]["participants"] if item["puuid"] == puuid),
                None,
            )
            if participant:
                matches.append(self._summarize_match(raw_match["info"], participant))
        return PlayerData(
            riot_id=f"{account.get('gameName', game_name)}#{account.get('tagLine', tag_line)}",
            level=int(summoner.get("summonerLevel", 0)) if isinstance(summoner, dict) else 0,
            ranks=ranks if isinstance(ranks, list) else [],
            matches=matches,
            profile_icon_id=int(summoner.get("profileIconId", 0)) if isinstance(summoner, dict) else 0,
            puuid=puuid,
            live_game=self.load_live_game(puuid) if include_live else None,
        )

    def load_live_game(self, puuid: str) -> dict | None:
        """Zwraca aktualną grę gracza lub None, gdy gracz nie jest w meczu."""
        game = self._get(
            self.platform,
            f"/lol/spectator/v5/active-games/by-summoner/{self._quote(puuid)}",
            allow_not_found=True,
        )
        if not isinstance(game, dict):
            return None
        return {
            "game_id": str(game.get("gameId", "")),
            "game_mode": game.get("gameMode", "Gra niestandardowa"),
            "queue_id": int(game.get("gameQueueConfigId", 0) or 0),
            "game_length": max(0, int(game.get("gameLength", 0) or 0)),
            "started_at": int(game.get("gameStartTime", 0) or 0),
            "participants": [
                {
                    "puuid": item.get("puuid", ""),
                    "riot_id": item.get("riotId")
                    or item.get("summonerName")
                    or "Gracz",
                    "team_id": int(item.get("teamId", 0) or 0),
                    "champion_id": int(item.get("championId", 0) or 0),
                    "profile_icon_id": int(item.get("profileIconId", 0) or 0),
                    "spell1_id": int(item.get("spell1Id", 0) or 0),
                    "spell2_id": int(item.get("spell2Id", 0) or 0),
                    "bot": bool(item.get("bot", False)),
                }
                for item in game.get("participants", [])
            ],
            "bans": [
                {
                    "team_id": int(item.get("teamId", 0) or 0),
                    "champion_id": int(item.get("championId", 0) or 0),
                    "pick_turn": int(item.get("pickTurn", 0) or 0),
                }
                for item in game.get("bannedChampions", [])
            ],
        }

    def load_ranks(self, puuid: str) -> list[dict]:
        ranks = self._get(
            self.platform,
            f"/lol/league/v4/entries/by-puuid/{self._quote(puuid)}",
        )
        return ranks if isinstance(ranks, list) else []

    def load_live_player_insight(
        self, puuid: str, champion_id: int, match_count: int = 5
    ) -> dict:
        """Analizuje krótką formę uczestnika aktywnego meczu."""
        match_ids = self._get(
            self.regional,
            f"/lol/match/v5/matches/by-puuid/{self._quote(puuid)}/ids"
            f"?start=0&count={max(1, min(5, int(match_count)))}",
        )
        results: list[bool] = []
        champion_games = 0
        for match_id in match_ids if isinstance(match_ids, list) else []:
            match = self._get(
                self.regional, f"/lol/match/v5/matches/{self._quote(match_id)}"
            )
            participant = next(
                (
                    item for item in match.get("info", {}).get("participants", [])
                    if item.get("puuid") == puuid
                ),
                None,
            )
            if not participant:
                continue
            results.append(bool(participant.get("win")))
            if int(participant.get("championId", 0) or 0) == int(champion_id):
                champion_games += 1
        streak_count = 0
        if results:
            first_result = results[0]
            streak_count = next(
                (index for index, result in enumerate(results) if result != first_result),
                len(results),
            )
        return {
            "puuid": puuid,
            "streak_result": "W" if results and results[0] else "L" if results else "—",
            "streak_count": streak_count,
            "champion_games": champion_games,
            "sample_size": len(results),
        }

    @staticmethod
    def _summarize_match(info: dict, participant: dict) -> dict:
        duration = int(info.get("gameDuration", 0))
        started_ms = int(info.get("gameStartTimestamp", 0))
        return {
            "result": "Wygrana" if participant.get("win") else "Przegrana",
            "champion": participant.get("championName", "?"),
            "kills": participant.get("kills", 0),
            "deaths": participant.get("deaths", 0),
            "assists": participant.get("assists", 0),
            "cs": int(participant.get("totalMinionsKilled", 0))
            + int(participant.get("neutralMinionsKilled", 0)),
            "damage": int(participant.get("totalDamageDealtToChampions", 0)),
            "gold": int(participant.get("goldEarned", 0)),
            "vision": int(participant.get("visionScore", 0)),
            "position": participant.get("teamPosition")
            or participant.get("individualPosition")
            or "UNKNOWN",
            "queue": QUEUE_NAMES.get(
                info.get("queueId"), f"Kolejka {info.get('queueId', '?')}"
            ),
            "queue_id": info.get("queueId"),
            "duration": f"{duration // 60}:{duration % 60:02d}",
            "duration_seconds": duration,
            "date": datetime.fromtimestamp(started_ms / 1000).strftime("%d.%m.%Y %H:%M")
            if started_ms else "—",
            "participants": [
                RiotApiClient._summarize_participant(item)
                for item in info.get("participants", [])
            ],
        }

    @staticmethod
    def _summarize_participant(participant: dict) -> dict:
        game_name = (
            participant.get("riotIdGameName")
            or participant.get("summonerName")
            or "Nieznany"
        )
        tag_line = participant.get("riotIdTagline")
        return {
            "puuid": participant.get("puuid", ""),
            "riot_id": f"{game_name}#{tag_line}" if tag_line else game_name,
            "champion": participant.get("championName", "?"),
            "kills": int(participant.get("kills", 0)),
            "deaths": int(participant.get("deaths", 0)),
            "assists": int(participant.get("assists", 0)),
            "cs": int(participant.get("totalMinionsKilled", 0))
            + int(participant.get("neutralMinionsKilled", 0)),
            "gold": int(participant.get("goldEarned", 0)),
            "damage": int(participant.get("totalDamageDealtToChampions", 0)),
            "vision": int(participant.get("visionScore", 0)),
            "position": participant.get("teamPosition")
            or participant.get("individualPosition")
            or "UNKNOWN",
            "team_id": int(participant.get("teamId", 0)),
            "win": bool(participant.get("win")),
            "items": [
                int(participant.get(f"item{slot}", 0)) for slot in range(7)
                if int(participant.get(f"item{slot}", 0)) > 0
            ],
        }
