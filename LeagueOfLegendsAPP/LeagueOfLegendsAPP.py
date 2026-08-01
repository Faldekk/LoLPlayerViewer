from __future__ import annotations

import json
from io import BytesIO
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:
    project_python = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
    current_python = Path(sys.executable).resolve()
    if __name__ == "__main__" and project_python.exists() and current_python != project_python.resolve():
        # Visual Studio może wybrać globalny interpreter bez zależności projektu.
        # Ponowne uruchomienie przez .venv zapewnia dostęp do Matplotlib.
        os.execv(
            str(project_python),
            [str(project_python), str(Path(__file__).resolve()), *sys.argv[1:]],
        )
    FigureCanvasTkAgg = None
    Figure = None

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


REGIONS = {
    "Europa Zachodnia (EUW)": ("euw1", "europe"),
    "Europa Pn.-Wsch. (EUNE)": ("eun1", "europe"),
    "Ameryka Północna (NA)": ("na1", "americas"),
    "Korea (KR)": ("kr", "asia"),
    "Brazylia (BR)": ("br1", "americas"),
    "Japonia (JP)": ("jp1", "asia"),
    "Turcja (TR)": ("tr1", "europe"),
    "Oceania (OCE)": ("oc1", "sea"),
}

QUEUE_NAMES = {
    400: "Normal Draft",
    420: "Solo/Duo",
    430: "Normal Blind",
    440: "Flex",
    450: "ARAM",
    490: "Quickplay",
    1700: "Arena",
    1750: "Arena (1750)",
}

class RiotApiError(Exception):
    """Czytelny dla użytkownika błąd Riot API."""


@dataclass(frozen=True)
class PlayerData:
    riot_id: str
    level: int
    ranks: list[dict]
    matches: list[dict]
    profile_icon_id: int = 0


class DataDragonAssets:
    """Pobiera i buforuje oficjalne grafiki League of Legends."""

    _version: str | None = None
    _bytes_cache: dict[tuple[str, str], bytes] = {}
    _lock = threading.Lock()

    @classmethod
    def _get_version(cls) -> str:
        with cls._lock:
            if cls._version:
                return cls._version
        request = urllib.request.Request(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            headers={"User-Agent": "LoL-Player-Viewer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            version = json.load(response)[0]
        with cls._lock:
            cls._version = version
        return version

    @classmethod
    def load(cls, kind: str, asset_id: str) -> bytes | None:
        key = (kind, str(asset_id))
        with cls._lock:
            if key in cls._bytes_cache:
                return cls._bytes_cache[key]
        try:
            version = cls._get_version()
            folder = "champion" if kind == "champion" else "item"
            safe_id = urllib.parse.quote(str(asset_id), safe="")
            url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/{folder}/{safe_id}.png"
            request = urllib.request.Request(url, headers={"User-Agent": "LoL-Player-Viewer/1.0"})
            with urllib.request.urlopen(request, timeout=12) as response:
                content = response.read()
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError):
            return None
        with cls._lock:
            cls._bytes_cache[key] = content
        return content


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
            raise RiotApiError(messages.get(error.code, f"Błąd Riot API (HTTP {error.code}).")) from error
        except urllib.error.URLError as error:
            raise RiotApiError("Nie można połączyć się z Riot API. Sprawdź internet.") from error
        except TimeoutError as error:
            raise RiotApiError("Riot API nie odpowiedziało na czas.") from error

    @staticmethod
    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    def load_player(self, game_name: str, tag_line: str, match_count: int = 30) -> PlayerData:
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
            "queue": QUEUE_NAMES.get(info.get("queueId"), f"Kolejka {info.get('queueId', '?')}"),
            "queue_id": info.get("queueId"),
            "duration": f"{duration // 60}:{duration % 60:02d}",
            "date": datetime.fromtimestamp(started_ms / 1000).strftime("%d.%m.%Y %H:%M") if started_ms else "—",
            "participants": [
                RiotApiClient._summarize_participant(item)
                for item in info.get("participants", [])
            ],
        }

    @staticmethod
    def _summarize_participant(participant: dict) -> dict:
        game_name = participant.get("riotIdGameName") or participant.get("summonerName") or "Nieznany"
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


class LolApp(tk.Tk):
    BG = "#f4f7fb"
    PANEL = "#ffffff"
    PANEL_ALT = "#edf2f8"
    BORDER = "#dce3ec"
    GOLD = "#2563eb"
    TEXT = "#172033"
    MUTED = "#687386"
    BLUE = "#16a36a"
    RED = "#dc4c64"

    def __init__(self) -> None:
        super().__init__()
        self.title("LoL Player Viewer")
        self.geometry("1050x720")
        self.minsize(900, 620)
        self.configure(bg=self.BG)
        self.icon_photos: dict[tuple[str, str, int], object] = {}
        self.match_by_row: dict[str, dict] = {}
        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("Card.TFrame", background=self.PANEL, relief="solid", borderwidth=1)
        style.configure(
            "TLabel", background=self.BG, foreground=self.TEXT, font=("Segoe UI", 10)
        )
        style.configure(
            "Title.TLabel", font=("Segoe UI Semibold", 26), foreground=self.TEXT
        )
        style.configure("Subtitle.TLabel", foreground=self.MUTED, font=("Segoe UI", 10))
        style.configure(
            "Eyebrow.TLabel", foreground=self.GOLD, font=("Segoe UI Semibold", 9)
        )
        style.configure(
            "CardTitle.TLabel", font=("Segoe UI Semibold", 17),
            background=self.PANEL, foreground=self.TEXT,
        )
        style.configure(
            "CardLabel.TLabel", background=self.PANEL, foreground=self.MUTED,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "CardMuted.TLabel", background=self.PANEL, foreground=self.MUTED,
        )
        style.configure(
            "Status.TLabel", background=self.PANEL, foreground=self.GOLD,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Accent.TButton", font=("Segoe UI Semibold", 10), padding=(20, 10),
            background=self.GOLD, foreground="#ffffff", borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#1d4ed8"), ("disabled", "#9aafcf")],
        )
        style.configure(
            "TEntry", padding=9, fieldbackground="#ffffff", foreground=self.TEXT,
            bordercolor=self.BORDER, lightcolor=self.BORDER, darkcolor=self.BORDER,
        )
        style.configure(
            "TCombobox", padding=8, fieldbackground="#ffffff", foreground=self.TEXT,
            bordercolor=self.BORDER, arrowcolor=self.MUTED,
        )
        style.configure(
            "Treeview", background=self.PANEL, fieldbackground=self.PANEL,
            foreground=self.TEXT, rowheight=36, borderwidth=0, font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading", background=self.PANEL_ALT, foreground=self.MUTED,
            font=("Segoe UI Semibold", 9), relief="flat", padding=(8, 9),
        )
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", self.TEXT)])
        style.configure("TNotebook", background=self.BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=self.BG, foreground=self.MUTED,
            padding=(18, 10), font=("Segoe UI Semibold", 10), borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.PANEL)],
            foreground=[("selected", self.GOLD)],
        )

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=(30, 24))
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 20))
        heading = ttk.Frame(header)
        heading.pack(side="left")
        ttk.Label(heading, text="LEAGUE STATS", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(heading, text="LoL Player Viewer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading, text="Sprawdź formę gracza, ranking i historię ostatnich gier.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        search = ttk.Frame(outer, style="Card.TFrame", padding=18)
        search.pack(fill="x", pady=(0, 16))
        self.riot_id_var = tk.StringVar()
        self.region_var = tk.StringVar(value="Europa Pn.-Wsch. (EUNE)")
        self.api_key_var = tk.StringVar(value=os.environ.get("RIOT_API_KEY", ""))

        ttk.Label(search, text="RIOT ID", style="CardLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(search, text="REGION", style="CardLabel.TLabel").grid(row=0, column=1, sticky="w", padx=(14, 0))
        ttk.Label(search, text="KLUCZ RIOT API", style="CardLabel.TLabel").grid(row=0, column=2, sticky="w", padx=(14, 0))
        self.riot_entry = ttk.Entry(search, textvariable=self.riot_id_var, width=38)
        self.riot_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        region_box = ttk.Combobox(search, textvariable=self.region_var, values=list(REGIONS), state="readonly", width=31)
        region_box.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(4, 0))
        self.api_key_entry = ttk.Entry(search, textvariable=self.api_key_var, show="•")
        self.api_key_entry.grid(row=1, column=2, sticky="ew", padx=(14, 0), pady=(4, 0))
        self.search_button = ttk.Button(
            search, text="Wyszukaj", style="Accent.TButton", command=self.search
        )
        self.search_button.grid(row=1, column=3, padx=(14, 0), pady=(4, 0))
        search.columnconfigure(0, weight=2)
        search.columnconfigure(1, weight=1)
        search.columnconfigure(2, weight=2)
        self.riot_entry.bind("<Return>", lambda _event: self.search())

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=4)
        content.columnconfigure(1, weight=1, minsize=285)
        content.rowconfigure(0, weight=1)

        cards = ttk.Frame(content)
        cards.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
        cards.columnconfigure(0, weight=1)
        for row in range(3):
            cards.rowconfigure(row, weight=1, uniform="profile_cards")

        profile = ttk.Frame(cards, style="Card.TFrame", padding=16)
        profile.grid(row=0, column=0, sticky="nsew", pady=(0, 6))
        ttk.Label(profile, text="GRACZ", style="CardLabel.TLabel").pack(anchor="w")
        profile_body = ttk.Frame(profile, style="Card.TFrame")
        profile_body.pack(fill="x", pady=(6, 0))
        self.profile_icon_label = ttk.Label(profile_body, text="", style="CardMuted.TLabel")
        self.profile_icon_label.pack(side="left", padx=(0, 9))
        profile_text = ttk.Frame(profile_body, style="Card.TFrame")
        profile_text.pack(side="left", fill="x", expand=True)
        self.player_label = ttk.Label(profile_text, text="Wyszukaj gracza", style="CardTitle.TLabel")
        self.player_label.pack(anchor="w")
        self.level_label = ttk.Label(profile_text, text="Poziom —", style="CardMuted.TLabel")
        self.level_label.pack(anchor="w", pady=(3, 0))
        self.status_label = ttk.Label(profile, text="GOTOWE", style="Status.TLabel")
        self.status_label.pack(anchor="w", pady=(9, 0))

        self.rank_labels = []
        for index in range(2):
            card = ttk.Frame(cards, style="Card.TFrame", padding=16)
            card.grid(
                row=index + 1, column=0, sticky="nsew",
                pady=(6, 0) if index else 6,
            )
            queue_label = "SOLO / DUO" if index == 0 else "FLEX 5V5"
            ttk.Label(card, text=queue_label, style="CardLabel.TLabel").pack(anchor="w")
            title = ttk.Label(card, text="Bez danych", style="CardTitle.TLabel")
            title.pack(anchor="w", pady=(5, 0))
            details = ttk.Label(card, text="Brak rozegranych gier", style="CardMuted.TLabel")
            details.pack(anchor="w", pady=(3, 0))
            self.rank_labels.append((title, details))

        self.notebook = ttk.Notebook(content)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        table_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=1)
        self.chart_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=12)
        self.notebook.add(table_tab, text="  Historia meczów  ")
        self.notebook.add(self.chart_tab, text="  Analiza ranked  ")

        table_header = ttk.Frame(table_tab, style="Card.TFrame", padding=(12, 8))
        table_header.pack(fill="x")
        ttk.Label(
            table_header,
            text="Kliknij dwukrotnie mecz, aby zobaczyć drużyny, statystyki i przedmioty",
            style="CardMuted.TLabel",
        ).pack(anchor="w")
        table_frame = ttk.Frame(table_tab, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)
        columns = ("result", "champion", "kda", "queue", "duration", "date")
        self.matches_tree = ttk.Treeview(table_frame, columns=columns, show="tree headings")
        self.matches_tree.heading("#0", text="")
        self.matches_tree.column("#0", width=48, minwidth=48, stretch=False, anchor="center")
        headings = {
            "result": "Wynik", "champion": "Bohater", "kda": "K / D / A",
            "queue": "Tryb", "duration": "Czas", "date": "Data",
        }
        widths = {"result": 100, "champion": 130, "kda": 110, "queue": 150, "duration": 70, "date": 150}
        for column in columns:
            self.matches_tree.heading(column, text=headings[column])
            self.matches_tree.column(column, width=widths[column], anchor="center")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.matches_tree.yview)
        self.matches_tree.configure(yscrollcommand=scrollbar.set)
        self.matches_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.matches_tree.tag_configure("win", foreground=self.BLUE)
        self.matches_tree.tag_configure("loss", foreground="#ff7676")
        self.matches_tree.bind("<Double-1>", self._open_selected_match)

        self.chart_placeholder = ttk.Label(
            self.chart_tab,
            text="Wyszukaj gracza, aby zobaczyć wykres meczów rankingowych.",
            style="CardMuted.TLabel",
        )
        self.chart_placeholder.pack(expand=True)
        self.chart_canvas = None

        self.riot_entry.focus_set()

    def search(self) -> None:
        raw_id = self.riot_id_var.get().strip()
        if "#" not in raw_id:
            messagebox.showwarning("Niepełne Riot ID", "Wpisz Riot ID w formacie Nazwa#TAG, np. Gracz#EUNE.")
            return
        game_name, tag_line = (part.strip() for part in raw_id.rsplit("#", 1))
        if not game_name or not tag_line:
            messagebox.showwarning("Niepełne Riot ID", "Nazwa i TAG nie mogą być puste.")
            return

        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror(
                "Brak klucza API",
                "Wklej klucz w pole „Klucz Riot API”. Klucz zaczyna się od RGAPI-.",
            )
            self.api_key_entry.focus_set()
            return

        platform, regional = REGIONS[self.region_var.get()]
        self._set_loading(True)
        client = RiotApiClient(api_key, platform, regional)
        threading.Thread(
            target=self._load_worker,
            args=(client, game_name, tag_line),
            daemon=True,
        ).start()

    def _load_worker(self, client: RiotApiClient, game_name: str, tag_line: str) -> None:
        try:
            data = client.load_player(game_name, tag_line)
        except RiotApiError as error:
            self.after(0, self._show_error, str(error))
        except (KeyError, TypeError, ValueError):
            self.after(0, self._show_error, "Riot API zwróciło dane w nieoczekiwanym formacie.")
        else:
            self.after(0, self._display_player, data)

    def _set_loading(self, loading: bool) -> None:
        self.search_button.configure(state="disabled" if loading else "normal")
        self.status_label.configure(text="POBIERANIE DANYCH…" if loading else "GOTOWE")
        if loading:
            self.configure(cursor="watch")
        else:
            self.configure(cursor="")

    def _show_error(self, message: str) -> None:
        self._set_loading(False)
        self.status_label.configure(text="BŁĄD POBIERANIA")
        messagebox.showerror("Błąd", message)

    def _display_player(self, data: PlayerData) -> None:
        self._set_loading(False)
        self.player_label.configure(text=data.riot_id)
        self.level_label.configure(text=f"Poziom {data.level}")
        self._load_profile_icon(data.profile_icon_id)

        ranks_by_queue = {entry.get("queueType"): entry for entry in data.ranks}
        for labels, queue_type in zip(self.rank_labels, ("RANKED_SOLO_5x5", "RANKED_FLEX_SR")):
            title, details = labels
            entry = ranks_by_queue.get(queue_type)
            if entry:
                tier = str(entry.get("tier", "")).title()
                division = entry.get("rank", "")
                lp = entry.get("leaguePoints", 0)
                wins = entry.get("wins", 0)
                losses = entry.get("losses", 0)
                games = wins + losses
                win_rate = round(wins / games * 100) if games else 0
                title.configure(text=f"{tier} {division}  ·  {lp} LP")
                details.configure(text=f"{wins} W / {losses} L  •  {win_rate}% zwycięstw")
            else:
                title.configure(text="Bez rangi")
                details.configure(text="Brak rozegranych gier rankingowych")

        for item in self.matches_tree.get_children():
            self.matches_tree.delete(item)
        self.match_by_row.clear()
        for match in data.matches:
            row_id = self.matches_tree.insert(
                "",
                "end",
                values=(
                    match["result"], match["champion"],
                    f"{match['kills']} / {match['deaths']} / {match['assists']}",
                    match["queue"], match["duration"], match["date"],
                ),
                tags=("win" if match["result"] == "Wygrana" else "loss",),
            )
            self.match_by_row[row_id] = match
        self._load_history_icons(data.matches)
        self._draw_ranked_chart(data.matches)
        self.status_label.configure(text=f"POBRANO {len(data.matches)} MECZÓW")

    @staticmethod
    def _photo_from_bytes(content: bytes, size: int):
        if Image is None or ImageTk is None:
            return None
        image = Image.open(BytesIO(content)).convert("RGBA")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def _load_history_icons(self, matches: list[dict]) -> None:
        if Image is None or ImageTk is None:
            return
        champions = {match["champion"] for match in matches if match.get("champion")}

        def worker() -> None:
            loaded = {
                champion: DataDragonAssets.load("champion", champion)
                for champion in champions
            }
            try:
                self.after(0, self._apply_history_icons, loaded)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _load_profile_icon(self, profile_icon_id: int) -> None:
        if not profile_icon_id or Image is None or ImageTk is None:
            return

        def worker() -> None:
            # Ikony profilu korzystają z tego samego CDN, ale z osobnego folderu.
            try:
                version = DataDragonAssets._get_version()
                url = (
                    f"https://ddragon.leagueoflegends.com/cdn/{version}/img/"
                    f"profileicon/{profile_icon_id}.png"
                )
                request = urllib.request.Request(
                    url, headers={"User-Agent": "LoL-Player-Viewer/1.0"}
                )
                with urllib.request.urlopen(request, timeout=12) as response:
                    content = response.read()
            except (urllib.error.URLError, TimeoutError, ValueError, IndexError):
                return
            try:
                self.after(0, self._apply_profile_icon, profile_icon_id, content)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_profile_icon(self, profile_icon_id: int, content: bytes) -> None:
        cache_key = ("profile", str(profile_icon_id), 52)
        photo = self.icon_photos.get(cache_key)
        if photo is None:
            photo = self._photo_from_bytes(content, 52)
            if photo is not None:
                self.icon_photos[cache_key] = photo
        if photo is not None:
            self.profile_icon_label.configure(image=photo)

    def _apply_history_icons(self, loaded: dict[str, bytes | None]) -> None:
        for row_id, match in self.match_by_row.items():
            if not self.matches_tree.exists(row_id):
                continue
            champion = match.get("champion", "")
            content = loaded.get(champion)
            if not content:
                continue
            cache_key = ("champion", champion, 28)
            photo = self.icon_photos.get(cache_key)
            if photo is None:
                photo = self._photo_from_bytes(content, 28)
                if photo is not None:
                    self.icon_photos[cache_key] = photo
            if photo is not None:
                self.matches_tree.item(row_id, image=photo)

    def _open_selected_match(self, _event=None) -> None:
        selected = self.matches_tree.selection()
        if not selected:
            return
        match = self.match_by_row.get(selected[0])
        if not match:
            return
        self._open_match_details(match)

    def _open_match_details(self, match: dict) -> None:
        window = tk.Toplevel(self)
        window.title(f"Szczegóły meczu — {match['champion']}")
        window.geometry("1040x680")
        window.minsize(900, 590)
        window.configure(bg=self.BG)
        window.transient(self)

        outer = ttk.Frame(window, padding=22)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 16))
        result_color = self.BLUE if match["result"] == "Wygrana" else self.RED
        tk.Label(
            header, text=match["result"].upper(), bg=self.BG, fg=result_color,
            font=("Segoe UI Semibold", 10),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"{match['champion']}  ·  {match['kills']} / {match['deaths']} / {match['assists']}",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=f"{match['queue']}  •  {match['duration']}  •  {match['date']}",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        teams_frame = ttk.Frame(outer)
        teams_frame.pack(fill="both", expand=True)
        teams_frame.columnconfigure(0, weight=1, uniform="teams")
        teams_frame.columnconfigure(1, weight=1, uniform="teams")
        teams_frame.rowconfigure(0, weight=1)

        participants = match.get("participants", [])
        team_ids = sorted({participant["team_id"] for participant in participants})
        if len(team_ids) < 2:
            team_ids = [100, 200]
        image_targets: dict[tuple[str, str], list[ttk.Label]] = {}

        for column, team_id in enumerate(team_ids[:2]):
            team = [participant for participant in participants if participant["team_id"] == team_id]
            won = bool(team and team[0]["win"])
            panel = ttk.Frame(teams_frame, style="Card.TFrame", padding=12)
            panel.grid(
                row=0, column=column, sticky="nsew",
                padx=(0, 7) if column == 0 else (7, 0),
            )
            team_title = "ZWYCIĘSTWO" if won else "PORAŻKA"
            tk.Label(
                panel, text=f"DRUŻYNA {column + 1}  ·  {team_title}",
                bg=self.PANEL, fg=self.BLUE if won else self.RED,
                font=("Segoe UI Semibold", 10),
            ).pack(anchor="w", pady=(0, 8))

            for participant in team:
                row = ttk.Frame(panel, style="Card.TFrame", padding=(5, 7))
                row.pack(fill="x")
                champion_label = ttk.Label(row, text="", style="CardMuted.TLabel", width=6)
                champion_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 7))
                image_targets.setdefault(
                    ("champion", participant["champion"]), []
                ).append(champion_label)

                ttk.Label(
                    row, text=participant["riot_id"], style="CardLabel.TLabel"
                ).grid(row=0, column=1, sticky="w")
                ttk.Label(
                    row,
                    text=(
                        f"{participant['champion']}  ·  "
                        f"{participant['kills']} / {participant['deaths']} / {participant['assists']}"
                    ),
                    style="CardMuted.TLabel",
                ).grid(row=1, column=1, sticky="w")
                ttk.Label(
                    row,
                    text=(
                        f"CS {participant['cs']}   DMG {participant['damage']:,}   "
                        f"GOLD {participant['gold']:,}   VIS {participant['vision']}"
                    ).replace(",", " "),
                    style="CardMuted.TLabel",
                ).grid(row=0, column=2, sticky="e", padx=(8, 0))

                items = ttk.Frame(row, style="Card.TFrame")
                items.grid(row=1, column=2, sticky="e", padx=(8, 0))
                for item_id in participant["items"][:7]:
                    item_label = ttk.Label(items, text="", style="CardMuted.TLabel", width=3)
                    item_label.pack(side="left", padx=1)
                    image_targets.setdefault(("item", str(item_id)), []).append(item_label)
                row.columnconfigure(1, weight=1)

        ttk.Label(
            outer,
            text="Dwuklik na innym meczu otworzy jego osobne szczegóły.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(10, 0))
        self._load_detail_icons(window, image_targets)

    def _load_detail_icons(
        self, window: tk.Toplevel, targets: dict[tuple[str, str], list[ttk.Label]]
    ) -> None:
        if Image is None or ImageTk is None:
            return

        def worker() -> None:
            loaded = {
                key: DataDragonAssets.load(key[0], key[1])
                for key in targets
            }
            try:
                self.after(0, self._apply_detail_icons, window, targets, loaded)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_detail_icons(
        self,
        window: tk.Toplevel,
        targets: dict[tuple[str, str], list[ttk.Label]],
        loaded: dict[tuple[str, str], bytes | None],
    ) -> None:
        if not window.winfo_exists():
            return
        if not hasattr(window, "photo_refs"):
            window.photo_refs = []
        for key, labels in targets.items():
            content = loaded.get(key)
            if not content:
                continue
            size = 42 if key[0] == "champion" else 24
            photo = self._photo_from_bytes(content, size)
            if photo is None:
                continue
            window.photo_refs.append(photo)
            for label in labels:
                if label.winfo_exists():
                    label.configure(image=photo, width=size // 8)

    def _draw_ranked_chart(self, matches: list[dict]) -> None:
        if self.chart_canvas is not None:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas = None
        self.chart_placeholder.pack_forget()

        ranked = [match for match in matches if match.get("queue_id") in (420, 440)]
        if Figure is None or FigureCanvasTkAgg is None:
            self.chart_placeholder.configure(
                text="Brak biblioteki Matplotlib. Uruchom: python -m pip install matplotlib"
            )
            self.chart_placeholder.pack(expand=True)
            return
        if not ranked:
            self.chart_placeholder.configure(
                text="Wśród pobranych meczów nie ma gier Solo/Duo ani Flex."
            )
            self.chart_placeholder.pack(expand=True)
            return

        # API zwraca najnowszy mecz jako pierwszy; wykres pokazuje upływ czasu w prawo.
        ranked.reverse()
        kda = [
            (match["kills"] + match["assists"]) / max(1, match["deaths"])
            for match in ranked
        ]
        colors = [self.BLUE if match["result"] == "Wygrana" else self.RED for match in ranked]
        wins = sum(match["result"] == "Wygrana" for match in ranked)
        win_rate = round(wins / len(ranked) * 100)
        x_values = list(range(1, len(ranked) + 1))

        figure = Figure(figsize=(9, 6), dpi=100, facecolor=self.PANEL, layout="constrained")
        axis = figure.add_subplot(111, facecolor=self.PANEL)
        axis.plot(x_values, kda, color=self.GOLD, linewidth=2, alpha=0.85, zorder=1)
        axis.scatter(
            x_values, kda, c=colors, s=65,
            edgecolors=self.TEXT, linewidths=0.7, zorder=2,
        )
        axis.axhline(3.0, color=self.MUTED, linestyle="--", linewidth=1, alpha=0.45)
        axis.set_title(
            f"Ranked: {wins} W / {len(ranked) - wins} L  •  {win_rate}% zwycięstw",
            color=self.TEXT, fontsize=13, fontweight="bold", pad=14,
        )
        axis.set_xlabel("Kolejne mecze (zielony = wygrana, czerwony = przegrana)", color=self.MUTED)
        axis.set_ylabel("KDA", color=self.MUTED)
        axis.tick_params(colors=self.MUTED)
        axis.grid(axis="y", color=self.BORDER, alpha=0.8)
        axis.spines[["top", "right"]].set_visible(False)
        axis.spines[["bottom", "left"]].set_color(self.BORDER)
        tick_step = max(1, (len(x_values) + 9) // 10)
        visible_ticks = x_values[::tick_step]
        if visible_ticks[-1] != x_values[-1]:
            visible_ticks.append(x_values[-1])
        axis.set_xticks(visible_ticks)
        axis.set_ylim(bottom=0)

        self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_tab)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    app = LolApp()
    app.mainloop()
