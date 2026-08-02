"""Nowoczesny interfejs HTML/CSS/JS uruchamiany w natywnym oknie WebView."""

from dataclasses import asdict
import os
from pathlib import Path
import sys
import time

try:
    import webview
except ImportError:
    project_python = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if project_python.exists() and current_python != project_python.resolve():
        os.execv(
            str(project_python),
            [str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        )
    raise SystemExit(
        "Brak PyWebView. Uruchom: python -m pip install -r requirements.txt"
    )

from assets import DataDragonAssets
from api_config import load_api_key
from config import REGIONS
from live_client import LiveClient
from riot_api import RiotApiClient, RiotApiError
from storage import ApiKeyStore, FavoritesStore


class AppBridge:
    def __init__(self) -> None:
        self.store = FavoritesStore()
        self.key_store = ApiKeyStore()
        self.live_client: RiotApiClient | None = None
        self.live_puuid = ""
        self.rank_cache: dict[str, list[dict]] = {}
        self.live_insight_cache: dict[tuple[str, int], tuple[float, dict]] = {}

    def bootstrap(self) -> dict:
        remembered_key = self.key_store.load()
        return {
            "regions": list(REGIONS),
            "favorites": self.store.load(),
            "api_key": remembered_key or load_api_key(),
            "api_key_saved": bool(remembered_key),
        }

    def _resolve_api_key(self, supplied_key: str) -> str:
        supplied_key = supplied_key.strip()
        remembered_key = self.key_store.load()
        configured_key = load_api_key()
        if supplied_key and supplied_key not in {remembered_key, configured_key}:
            return supplied_key
        return remembered_key or configured_key or supplied_key

    def _api_error(self, error: RiotApiError, attempted_key: str) -> dict:
        invalid = error.status_code in (401, 403)
        if invalid and self.key_store.load() == attempted_key:
            try:
                self.key_store.clear()
            except OSError:
                pass
        return {"ok": False, "error": str(error), "api_key_invalid": invalid}

    def search(
        self, riot_id: str, region_name: str, api_key: str, match_count: int = 30
    ) -> dict:
        riot_id = riot_id.strip()
        api_key = self._resolve_api_key(api_key)
        if "#" not in riot_id:
            return {"ok": False, "error": "Wpisz Riot ID w formacie Nazwa#TAG."}
        if region_name not in REGIONS:
            return {"ok": False, "error": "Wybierz prawidłowy region."}
        if not api_key:
            return {"ok": False, "error": "Wklej aktualny klucz Riot API."}
        game_name, tag_line = (part.strip() for part in riot_id.rsplit("#", 1))
        if not game_name or not tag_line:
            return {"ok": False, "error": "Nazwa i TAG nie mogą być puste."}
        platform, regional = REGIONS[region_name]
        try:
            client = RiotApiClient(api_key, platform, regional)
            player = client.load_player(game_name, tag_line, int(match_count))
            try:
                self.key_store.save(api_key)
            except OSError:
                pass
            self.live_client, self.live_puuid = client, player.puuid
            self.rank_cache.clear()
            try:
                version = DataDragonAssets.get_version()
                champion_map = DataDragonAssets.get_champion_map()
            except Exception:
                version = None
                champion_map = {}
            try:
                item_map = DataDragonAssets.get_item_map()
            except Exception:
                item_map = {}
        except RiotApiError as error:
            return self._api_error(error, api_key)
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "Riot API zwróciło nieoczekiwane dane."}
        return {"ok": True, "player": asdict(player), "ddragon_version": version, "champion_map": champion_map, "item_map": item_map, "api_key_saved": True}

    def refresh_live_game(self) -> dict:
        if self.live_client is None or not self.live_puuid:
            return {"ok": False, "error": "Najpierw wyszukaj gracza."}
        try:
            game = self.live_client.load_live_game(self.live_puuid)
        except RiotApiError as error:
            return self._api_error(error, self.live_client.api_key)
        return {"ok": True, "live_game": game}

    def local_live_stats(self) -> dict:
        return {"ok": True, "live_stats": LiveClient.load()}

    def live_player_insights(self, participants: list[dict]) -> dict:
        if self.live_client is None:
            return {"ok": False, "error": "Najpierw wyszukaj gracza."}
        insights = []
        now = time.monotonic()
        try:
            for item in participants[:10]:
                puuid = str(item.get("puuid", "")).strip()
                champion_id = int(item.get("champion_id", 0) or 0)
                if not puuid or champion_id <= 0:
                    continue
                key = (puuid, champion_id)
                cached = self.live_insight_cache.get(key)
                if cached and cached[0] > now:
                    insight = cached[1]
                else:
                    insight = self.live_client.load_live_player_insight(
                        puuid, champion_id, 5
                    )
                    self.live_insight_cache[key] = (now + 300, insight)
                insights.append(insight)
        except RiotApiError as error:
            return self._api_error(error, self.live_client.api_key)
        return {"ok": True, "insights": insights}

    def participant_ranks(self, puuids: list[str]) -> dict:
        if self.live_client is None:
            return {"ok": False, "error": "Najpierw wyszukaj gracza."}
        unique = list(dict.fromkeys(value for value in puuids if value))[:10]
        try:
            for puuid in unique:
                if puuid not in self.rank_cache:
                    self.rank_cache[puuid] = self.live_client.load_ranks(puuid)
        except RiotApiError as error:
            return self._api_error(error, self.live_client.api_key)
        return {
            "ok": True,
            "ranks": {puuid: self.rank_cache.get(puuid, []) for puuid in unique},
        }

    def compare_player(
        self, riot_id: str, region_name: str, api_key: str, match_count: int = 20
    ) -> dict:
        riot_id, api_key = riot_id.strip(), self._resolve_api_key(api_key)
        if "#" not in riot_id:
            return {"ok": False, "error": "Wpisz drugie Riot ID w formacie Nazwa#TAG."}
        if region_name not in REGIONS or not api_key:
            return {"ok": False, "error": "Sprawdź region i klucz Riot API."}
        game_name, tag_line = (part.strip() for part in riot_id.rsplit("#", 1))
        platform, regional = REGIONS[region_name]
        try:
            player = RiotApiClient(api_key, platform, regional).load_player(
                game_name, tag_line, min(30, max(10, int(match_count))),
                include_live=False,
            )
        except RiotApiError as error:
            return self._api_error(error, api_key)
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "Riot API zwróciło nieoczekiwane dane."}
        return {"ok": True, "player": asdict(player)}

    def toggle_favorite(self, riot_id: str, region: str) -> dict:
        favorites = self.store.load()
        target = next(
            (
                index for index, item in enumerate(favorites)
                if item["riot_id"].casefold() == riot_id.casefold()
                and item["region"] == region
            ),
            None,
        )
        if target is None:
            favorites.append({"riot_id": riot_id, "region": region})
            favorites.sort(key=lambda item: item["riot_id"].casefold())
            saved = True
        else:
            favorites.pop(target)
            saved = False
        try:
            self.store.save(favorites)
        except OSError as error:
            return {"ok": False, "error": f"Nie udało się zapisać ulubionych: {error}"}
        return {"ok": True, "saved": saved, "favorites": favorites}


def main() -> None:
    html_path = Path(__file__).resolve().parent / "web" / "index.html"
    webview.create_window(
        "LoL Player Viewer",
        url=str(html_path),
        js_api=AppBridge(),
        width=1280,
        height=820,
        min_size=(980, 650),
        background_color="#080b14",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
