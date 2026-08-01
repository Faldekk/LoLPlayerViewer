"""Nowoczesny interfejs HTML/CSS/JS uruchamiany w natywnym oknie WebView."""

from dataclasses import asdict
import os
from pathlib import Path
import sys

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
from config import REGIONS
from riot_api import RiotApiClient, RiotApiError
from storage import FavoritesStore


class AppBridge:
    def __init__(self) -> None:
        self.store = FavoritesStore()
        self.live_client: RiotApiClient | None = None
        self.live_puuid = ""

    def bootstrap(self) -> dict:
        return {"regions": list(REGIONS), "favorites": self.store.load()}

    def search(
        self, riot_id: str, region_name: str, api_key: str, match_count: int = 30
    ) -> dict:
        riot_id = riot_id.strip()
        api_key = api_key.strip()
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
            self.live_client, self.live_puuid = client, player.puuid
            try:
                version = DataDragonAssets.get_version()
                champion_map = DataDragonAssets.get_champion_map()
            except Exception:
                version = None
                champion_map = {}
        except RiotApiError as error:
            return {"ok": False, "error": str(error)}
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "Riot API zwróciło nieoczekiwane dane."}
        return {"ok": True, "player": asdict(player), "ddragon_version": version, "champion_map": champion_map}

    def refresh_live_game(self) -> dict:
        if self.live_client is None or not self.live_puuid:
            return {"ok": False, "error": "Najpierw wyszukaj gracza."}
        try:
            game = self.live_client.load_live_game(self.live_puuid)
        except RiotApiError as error:
            return {"ok": False, "error": str(error)}
        return {"ok": True, "live_game": game}

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
