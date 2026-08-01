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


class RiotApiClient:
    def __init__(self, api_key: str, platform: str, regional: str) -> None:
        self.api_key = api_key
        self.platform = platform
        self.regional = regional

    def _get(self, host: str, path: str):
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
                messages.get(error.code, f"Błąd Riot API (HTTP {error.code}).")
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
        self, game_name: str, tag_line: str, match_count: int = 30
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
        )

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
            "team_id": int(participant.get("teamId", 0)),
            "win": bool(participant.get("win")),
            "items": [
                int(participant.get(f"item{slot}", 0)) for slot in range(7)
                if int(participant.get(f"item{slot}", 0)) > 0
            ],
        }
