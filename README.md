# LoL Player Viewer

Desktopowa aplikacja napisana w Pythonie, która pobiera dane gracza z oficjalnego Riot Games API. Pozwala sprawdzić aktualną rangę, statystyki kolejek rankingowych oraz historię ostatnich meczów.

## Funkcje

- wyszukiwanie konta przez Riot ID w formacie `Nazwa#TAG`,
- obsługa EUW, EUNE, NA, KR, BR, JP, TR oraz OCE,
- poziom konta oraz rangi Solo/Duo i Flex,
- liczba zwycięstw, porażek i aktualny win rate,
- tabela 30 ostatnich meczów,
- wybór pobierania 10, 20, 30 lub 50 ostatnich meczów,
- filtrowanie historii po trybie, wyniku i nazwie bohatera,
- ikony profilu, bohaterów i przedmiotów z oficjalnego Data Dragon,
- bohater, K/D/A, tryb gry, czas trwania i data każdego meczu,
- szczegóły meczu otwierane dwuklikiem,
- składy obu drużyn, CS, obrażenia, gold, vision i komplet przedmiotów,
- wykres Matplotlib dla meczów Solo/Duo i Flex,
- osobna analiza 30 gier: win rate, średnie KDA, CS/min, obrażenia i vision,
- ranking najczęściej granych bohaterów z ich win rate i KDA,
- oznaczenie zwycięstw i porażek kolorami,
- pobieranie danych w tle bez zawieszania interfejsu,
- bezpieczne, zamaskowane pole na klucz Riot API.

## Wymagania

- Windows 10 lub Windows 11,
- Python 3.10 lub nowszy,
- dostęp do internetu,
- klucz z [Riot Developer Portal](https://developer.riotgames.com/).

## Instalacja

Otwórz PowerShell i sklonuj repozytorium:

```powershell
git clone https://github.com/Faldekk/LoLPlayerViewer.git
cd LoLPlayerViewer
```

Utwórz lokalne środowisko Pythona:

```powershell
python -m venv .venv
```

Aktywuj środowisko:

```powershell
.\.venv\Scripts\Activate.ps1
```

Zainstaluj zależności:

```powershell
python -m pip install -r .\requirements.txt
```

## Uruchomienie

Z aktywnym środowiskiem wykonaj:

```powershell
python .\LeagueOfLegendsAPP\LeagueOfLegendsAPP.py
```

Można też uruchomić program bez aktywowania środowiska:

```powershell
.\.venv\Scripts\python.exe .\LeagueOfLegendsAPP\LeagueOfLegendsAPP.py
```

Na Windows możesz również dwukrotnie kliknąć plik `Uruchom_LoL_Player_Viewer.cmd`. Skrypt zawsze wybierze projektowe środowisko `.venv`, w którym zainstalowany jest Matplotlib.

W Visual Studio jako interpreter projektu wybierz:

```text
.venv\Scripts\python.exe
```

Jeżeli Visual Studio uruchomi inny interpreter bez Matplotlib, aplikacja automatycznie przełączy się na lokalne środowisko `.venv`.

## Klucz Riot API

1. Zaloguj się na [Riot Developer Portal](https://developer.riotgames.com/).
2. Skopiuj klucz zaczynający się od `RGAPI-`.
3. Uruchom LoL Player Viewer.
4. Wklej klucz w zamaskowane pole **Klucz Riot API**.

Klucz jest przechowywany wyłącznie w pamięci podczas działania programu. Nie jest zapisywany na dysku ani wysyłany do repozytorium.

Opcjonalnie możesz ustawić zmienną środowiskową `RIOT_API_KEY`. Aplikacja automatycznie użyje jej jako wartości początkowej:

```powershell
$env:RIOT_API_KEY="RGAPI-TWOJ_KLUCZ"
```

Klucz deweloperski Riot zazwyczaj wygasa po 24 godzinach. Po wygaśnięciu wygeneruj nowy klucz w portalu i wklej go ponownie.

## Korzystanie z aplikacji

1. Wprowadź Riot ID, na przykład `NazwaGracza#EUNE`.
2. Wybierz region, na którym znajduje się konto.
3. Wklej aktualny klucz API.
4. Kliknij **Wyszukaj**.
5. Przełączaj się między zakładkami **Historia meczów**, **Analiza ranked** i **Statystyki**.
6. Kliknij dwukrotnie wybrany mecz, aby otworzyć szczegółowe statystyki obu drużyn.

Nad historią możesz połączyć kilka filtrów, na przykład pokazać wyłącznie wygrane mecze ranked wybranym bohaterem. Filtry działają lokalnie i nie wykonują dodatkowych zapytań do Riot API.

Pobranie 30 szczegółowych meczów może potrwać kilka–kilkanaście sekund. Przy przekroczeniu limitu zapytań aplikacja wyświetli odpowiedni komunikat.

## Struktura projektu

```text
LoLPlayerViewer/
├── LeagueOfLegendsAPP/
│   ├── LeagueOfLegendsAPP.py
│   └── LeagueOfLegendsAPP.pyproj
├── LeagueOfLegendsAPP.sln
├── requirements.txt
├── .gitignore
└── README.md
```

## Bezpieczeństwo

- Nie publikuj swojego klucza API.
- Nie wpisuj prawdziwego klucza bezpośrednio do kodu.
- Pliki `.env`, `config.json` i `secrets.json` są ignorowane przez Git.
- Jeżeli klucz trafił do publicznego repozytorium, natychmiast wygeneruj nowy w Riot Developer Portal.

## Informacja prawna

LoL Player Viewer nie jest wspierany ani zatwierdzony przez Riot Games i nie odzwierciedla poglądów ani opinii Riot Games ani osób oficjalnie zaangażowanych w produkcję lub zarządzanie właściwościami Riot Games. Riot Games oraz wszystkie powiązane właściwości są znakami towarowymi lub zastrzeżonymi znakami towarowymi Riot Games, Inc.
