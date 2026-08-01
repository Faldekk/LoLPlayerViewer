from __future__ import annotations

from io import BytesIO
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from assets import DataDragonAssets
from config import REGIONS
from models import PlayerData
from riot_api import RiotApiClient, RiotApiError
from storage import FavoritesStore

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
        self.current_matches: list[dict] = []
        self.current_player: dict[str, str] | None = None
        self.favorites_store = FavoritesStore()
        self.favorites = self.favorites_store.load()
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
            "Metric.TLabel", background=self.PANEL, foreground=self.TEXT,
            font=("Segoe UI Semibold", 22),
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

        favorites_box = ttk.Frame(header)
        favorites_box.pack(side="right", anchor="s")
        ttk.Label(favorites_box, text="ULUBIENI", style="Eyebrow.TLabel").pack(anchor="w")
        favorites_controls = ttk.Frame(favorites_box)
        favorites_controls.pack(pady=(4, 0))
        self.favorite_var = tk.StringVar()
        self.favorite_combo = ttk.Combobox(
            favorites_controls, textvariable=self.favorite_var,
            state="readonly", width=29,
        )
        self.favorite_combo.pack(side="left")
        self.favorite_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self._load_selected_favorite()
        )
        self._refresh_favorites()

        search = ttk.Frame(outer, style="Card.TFrame", padding=18)
        search.pack(fill="x", pady=(0, 16))
        self.riot_id_var = tk.StringVar()
        self.region_var = tk.StringVar(value="Europa Pn.-Wsch. (EUNE)")
        self.api_key_var = tk.StringVar(value=os.environ.get("RIOT_API_KEY", ""))
        self.match_count_var = tk.StringVar(value="30")

        ttk.Label(search, text="RIOT ID", style="CardLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(search, text="REGION", style="CardLabel.TLabel").grid(row=0, column=1, sticky="w", padx=(14, 0))
        ttk.Label(search, text="KLUCZ RIOT API", style="CardLabel.TLabel").grid(row=0, column=2, sticky="w", padx=(14, 0))
        ttk.Label(search, text="MECZE", style="CardLabel.TLabel").grid(row=0, column=3, sticky="w", padx=(14, 0))
        self.riot_entry = ttk.Entry(search, textvariable=self.riot_id_var, width=38)
        self.riot_entry.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        region_box = ttk.Combobox(search, textvariable=self.region_var, values=list(REGIONS), state="readonly", width=31)
        region_box.grid(row=1, column=1, sticky="ew", padx=(14, 0), pady=(4, 0))
        self.api_key_entry = ttk.Entry(search, textvariable=self.api_key_var, show="•")
        self.api_key_entry.grid(row=1, column=2, sticky="ew", padx=(14, 0), pady=(4, 0))
        match_count_box = ttk.Combobox(
            search, textvariable=self.match_count_var,
            values=("10", "20", "30", "50"), state="readonly", width=5,
        )
        match_count_box.grid(row=1, column=3, sticky="ew", padx=(14, 0), pady=(4, 0))
        self.search_button = ttk.Button(
            search, text="Wyszukaj", style="Accent.TButton", command=self.search
        )
        self.search_button.grid(row=1, column=4, padx=(14, 0), pady=(4, 0))
        search.columnconfigure(0, weight=2)
        search.columnconfigure(1, weight=1)
        search.columnconfigure(2, weight=2)
        search.columnconfigure(3, weight=0)
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
        self.favorite_button = ttk.Button(
            profile, text="☆ Dodaj do ulubionych", command=self._toggle_favorite
        )
        self.favorite_button.pack(anchor="w", pady=(8, 0))
        self._update_favorite_button()

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
        self.stats_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding=14)
        self.notebook.add(table_tab, text="  Historia meczów  ")
        self.notebook.add(self.chart_tab, text="  Analiza ranked  ")
        self.notebook.add(self.stats_tab, text="  Statystyki  ")

        table_header = ttk.Frame(table_tab, style="Card.TFrame", padding=(10, 7))
        table_header.pack(fill="x")
        ttk.Label(
            table_header,
            text="FILTRY",
            style="CardLabel.TLabel",
        ).pack(side="left", padx=(0, 8))
        self.history_queue_var = tk.StringVar(value="Wszystkie tryby")
        self.history_result_var = tk.StringVar(value="Wszystkie wyniki")
        self.history_champion_var = tk.StringVar()
        queue_filter = ttk.Combobox(
            table_header, textvariable=self.history_queue_var,
            values=("Wszystkie tryby", "Ranked", "Normal", "ARAM", "Arena"),
            state="readonly", width=15,
        )
        queue_filter.pack(side="left", padx=(0, 6))
        result_filter = ttk.Combobox(
            table_header, textvariable=self.history_result_var,
            values=("Wszystkie wyniki", "Wygrane", "Przegrane"),
            state="readonly", width=16,
        )
        result_filter.pack(side="left", padx=(0, 6))
        champion_filter = ttk.Entry(
            table_header, textvariable=self.history_champion_var, width=17
        )
        champion_filter.pack(side="left")
        self.filter_count_label = ttk.Label(
            table_header, text="", style="CardMuted.TLabel"
        )
        self.filter_count_label.pack(side="right")
        for widget in (queue_filter, result_filter):
            widget.bind("<<ComboboxSelected>>", lambda _event: self._apply_match_filters())
        champion_filter.bind("<KeyRelease>", lambda _event: self._apply_match_filters())
        champion_filter.insert(0, "")
        ttk.Label(
            table_tab,
            text="Dwuklik otwiera drużyny, statystyki i przedmioty wybranego meczu",
            style="CardMuted.TLabel",
            padding=(12, 6),
        ).pack(fill="x")
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

        metrics = ttk.Frame(self.stats_tab, style="Card.TFrame")
        metrics.pack(fill="x", pady=(0, 14))
        self.metric_labels: dict[str, ttk.Label] = {}
        metric_definitions = (
            ("win_rate", "WIN RATE"),
            ("kda", "ŚREDNIE KDA"),
            ("cs_min", "ŚREDNIE CS / MIN"),
            ("damage", "ŚREDNIE OBRAŻENIA"),
        )
        for column, (key, title) in enumerate(metric_definitions):
            card = ttk.Frame(metrics, style="Card.TFrame", padding=12)
            card.grid(
                row=0, column=column, sticky="nsew",
                padx=(0, 5) if column < len(metric_definitions) - 1 else 0,
            )
            ttk.Label(card, text=title, style="CardLabel.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="—", style="Metric.TLabel")
            value.pack(anchor="w", pady=(4, 0))
            self.metric_labels[key] = value
            metrics.columnconfigure(column, weight=1, uniform="metrics")

        stats_header = ttk.Frame(self.stats_tab, style="Card.TFrame")
        stats_header.pack(fill="x", pady=(0, 7))
        ttk.Label(
            stats_header, text="NAJCZĘŚCIEJ GRANI BOHATEROWIE", style="CardLabel.TLabel"
        ).pack(side="left")
        self.stats_summary_label = ttk.Label(
            stats_header, text="", style="CardMuted.TLabel"
        )
        self.stats_summary_label.pack(side="right")

        champion_columns = ("champion", "games", "record", "win_rate", "kda")
        self.champion_tree = ttk.Treeview(
            self.stats_tab, columns=champion_columns, show="headings", height=8
        )
        champion_headings = {
            "champion": "Bohater", "games": "Gry", "record": "W / L",
            "win_rate": "Win rate", "kda": "KDA",
        }
        champion_widths = {
            "champion": 190, "games": 70, "record": 100,
            "win_rate": 100, "kda": 90,
        }
        for column in champion_columns:
            self.champion_tree.heading(column, text=champion_headings[column])
            self.champion_tree.column(
                column, width=champion_widths[column], anchor="center"
            )
        self.champion_tree.tag_configure("positive", foreground=self.BLUE)
        self.champion_tree.tag_configure("negative", foreground=self.RED)
        self.champion_tree.pack(fill="both", expand=True)

        self.riot_entry.focus_set()

    @staticmethod
    def _favorite_label(favorite: dict[str, str]) -> str:
        return f"{favorite['riot_id']}  ·  {favorite['region']}"

    def _refresh_favorites(self) -> None:
        labels = [self._favorite_label(item) for item in self.favorites]
        self.favorite_combo.configure(values=labels)
        if self.favorite_var.get() not in labels:
            self.favorite_var.set("")

    def _current_favorite_index(self) -> int | None:
        if not self.current_player:
            return None
        riot_id = self.current_player["riot_id"].casefold()
        region = self.current_player["region"]
        for index, favorite in enumerate(self.favorites):
            if favorite["riot_id"].casefold() == riot_id and favorite["region"] == region:
                return index
        return None

    def _update_favorite_button(self) -> None:
        if not self.current_player:
            self.favorite_button.configure(text="☆ Dodaj do ulubionych", state="disabled")
        elif self._current_favorite_index() is None:
            self.favorite_button.configure(text="☆ Dodaj do ulubionych", state="normal")
        else:
            self.favorite_button.configure(text="★ Usuń z ulubionych", state="normal")

    def _toggle_favorite(self) -> None:
        if not self.current_player:
            return
        index = self._current_favorite_index()
        if index is None:
            self.favorites.append(dict(self.current_player))
            self.favorites.sort(key=lambda item: item["riot_id"].casefold())
        else:
            self.favorites.pop(index)
        try:
            self.favorites_store.save(self.favorites)
        except OSError as error:
            messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać ulubionych:\n{error}")
            self.favorites = self.favorites_store.load()
        self._refresh_favorites()
        self._update_favorite_button()

    def _load_selected_favorite(self) -> None:
        index = self.favorite_combo.current()
        if index < 0 or index >= len(self.favorites):
            return
        favorite = self.favorites[index]
        self.riot_id_var.set(favorite["riot_id"])
        self.region_var.set(favorite["region"])
        if self.api_key_var.get().strip():
            self.search()
        else:
            self.api_key_entry.focus_set()

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
            args=(client, game_name, tag_line, int(self.match_count_var.get())),
            daemon=True,
        ).start()

    def _load_worker(
        self, client: RiotApiClient, game_name: str, tag_line: str, match_count: int
    ) -> None:
        try:
            data = client.load_player(game_name, tag_line, match_count)
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
        self.current_player = {"riot_id": data.riot_id, "region": self.region_var.get()}
        self._update_favorite_button()
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

        self.current_matches = list(data.matches)
        self._apply_match_filters()
        self._draw_ranked_chart(data.matches)
        self._draw_statistics(data.matches)
        self.status_label.configure(text=f"POBRANO {len(data.matches)} MECZÓW")

    def _apply_match_filters(self) -> None:
        queue_filter = self.history_queue_var.get()
        result_filter = self.history_result_var.get()
        champion_filter = self.history_champion_var.get().strip().casefold()

        queue_groups = {
            "Ranked": {420, 440},
            "Normal": {400, 430, 490},
            "ARAM": {450},
            "Arena": {1700, 1750},
        }
        filtered = []
        for match in self.current_matches:
            if queue_filter in queue_groups and match.get("queue_id") not in queue_groups[queue_filter]:
                continue
            if result_filter == "Wygrane" and match.get("result") != "Wygrana":
                continue
            if result_filter == "Przegrane" and match.get("result") != "Przegrana":
                continue
            if champion_filter and champion_filter not in str(match.get("champion", "")).casefold():
                continue
            filtered.append(match)

        for item in self.matches_tree.get_children():
            self.matches_tree.delete(item)
        self.match_by_row.clear()
        for match in filtered:
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
        self.filter_count_label.configure(
            text=f"Pokazano {len(filtered)} z {len(self.current_matches)}"
        )
        self._load_history_icons(filtered)

    def _draw_statistics(self, matches: list[dict]) -> None:
        for row_id in self.champion_tree.get_children():
            self.champion_tree.delete(row_id)
        if not matches:
            for label in self.metric_labels.values():
                label.configure(text="—")
            self.stats_summary_label.configure(text="Brak danych")
            return

        games = len(matches)
        wins = sum(match.get("result") == "Wygrana" for match in matches)
        average_kda = sum(
            (match.get("kills", 0) + match.get("assists", 0))
            / max(1, match.get("deaths", 0))
            for match in matches
        ) / games
        cs_per_minute = []
        for match in matches:
            minutes = match.get("duration_seconds", 0) / 60
            if minutes > 0:
                cs_per_minute.append(match.get("cs", 0) / minutes)
        average_cs = sum(cs_per_minute) / len(cs_per_minute) if cs_per_minute else 0
        average_damage = sum(match.get("damage", 0) for match in matches) / games
        average_vision = sum(match.get("vision", 0) for match in matches) / games

        self.metric_labels["win_rate"].configure(text=f"{wins / games * 100:.0f}%")
        self.metric_labels["kda"].configure(text=f"{average_kda:.2f}")
        self.metric_labels["cs_min"].configure(text=f"{average_cs:.1f}")
        self.metric_labels["damage"].configure(text=f"{average_damage:,.0f}".replace(",", " "))
        self.stats_summary_label.configure(
            text=f"{games} gier  •  średni vision score {average_vision:.1f}"
        )

        champions: dict[str, dict[str, int]] = {}
        for match in matches:
            champion = match.get("champion", "Nieznany")
            stats = champions.setdefault(
                champion,
                {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0},
            )
            stats["games"] += 1
            stats["wins"] += match.get("result") == "Wygrana"
            stats["kills"] += int(match.get("kills", 0))
            stats["deaths"] += int(match.get("deaths", 0))
            stats["assists"] += int(match.get("assists", 0))

        ranking = sorted(
            champions.items(),
            key=lambda item: (item[1]["games"], item[1]["wins"]),
            reverse=True,
        )
        for champion, stats in ranking[:10]:
            losses = stats["games"] - stats["wins"]
            win_rate = stats["wins"] / stats["games"] * 100
            kda = (stats["kills"] + stats["assists"]) / max(1, stats["deaths"])
            tag = "positive" if win_rate >= 50 else "negative"
            self.champion_tree.insert(
                "", "end",
                values=(
                    champion, stats["games"], f"{stats['wins']} / {losses}",
                    f"{win_rate:.0f}%", f"{kda:.2f}",
                ),
                tags=(tag,),
            )

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
            content = DataDragonAssets.load("profile", profile_icon_id)
            if not content:
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
