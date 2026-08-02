# LoL Player Viewer

Desktopowa aplikacja z backendem Python i nowoczesnym interfejsem HTML/CSS/JavaScript, która pobiera dane gracza z oficjalnego Riot Games API. Pozwala sprawdzić aktualną rangę, statystyki kolejek rankingowych oraz historię ostatnich meczów.

## Funkcje

- wyszukiwanie konta przez Riot ID w formacie `Nazwa#TAG`,
- obsługa EUW, EUNE, NA, KR, BR, JP, TR oraz OCE,
- poziom konta oraz rangi Solo/Duo i Flex,
- liczba zwycięstw, porażek i aktualny win rate,
- tabela 30 ostatnich meczów,
- wybór pobierania 10, 20, 30 lub 50 ostatnich meczów,
- filtrowanie historii po trybie, wyniku i nazwie bohatera,
- lokalna lista ulubionych graczy z szybkim ponownym wyszukiwaniem,
- ikony profilu, bohaterów i przedmiotów z oficjalnego Data Dragon,
- bohater, K/D/A, tryb gry, czas trwania i data każdego meczu,
- szczegóły meczu otwierane dwuklikiem,
- składy obu drużyn, CS, obrażenia, gold, vision i komplet przedmiotów,
- interaktywny wykres KDA dla meczów Solo/Duo i Flex,
- osobna analiza 30 gier: win rate, średnie KDA, CS/min, obrażenia i vision,
- ranking najczęściej granych bohaterów z ich win rate i KDA,
- oznaczenie zwycięstw i porażek kolorami,
- pobieranie danych w tle bez zawieszania interfejsu,
- bezpieczne, zamaskowane pole na klucz Riot API.

### Live Game

Zakładka Live Game pokazuje aktywny mecz wyszukanego gracza: obie drużyny, championów, summoner spelle oraz aktualny czas gry. Dane odświeżają się automatycznie co 60 sekund lub po użyciu przycisku Odśwież.

Jeśli LoL działa na tym samym komputerze i wyszukane Riot ID należy do aktywnego gracza, aplikacja używa lokalnego Live Client Data API. Pokazuje wtedy aktualne K/D/A, CS, vision, poziomy, itemy, czas odrodzenia i bieżący gold, odświeżając dane co 5 sekund.

### Rozszerzone analizy

- analiza skuteczności na pozycjach Top, Jungle, Mid, ADC i Support,
- porównanie dwóch graczy: ranga, win rate, KDA, CS/min, obrażenia i champion pool,
- wykres z metrykami KDA, CS/min, obrażenia, vision i kroczący win rate,
- szczegółowa karta każdego championa po kliknięciu w Champion Pool,
- wykrywanie serii zwycięstw lub porażek oraz wizualizacja ostatnich 10 wyników,
- trwałe ustawienia motywu, koloru akcentu, regionu, liczby meczów i live refresh.
- interaktywne tooltipy itemów z polskim opisem, ceną zakupu i sprzedaży,
- tooltipy wyników W/L z pełnymi statystykami wskazanego meczu,
- forma uczestników Live Game: streak oraz gry obecnym championem w ostatnich 5 meczach,

## Wymagania

- Windows 10 lub Windows 11,
- Python 3.10 lub nowszy,
- Microsoft Edge WebView2 Runtime (standardowo obecny w Windows 10/11),
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
python .\LeagueOfLegendsAPP\web_ui.py
```

Można też uruchomić program bez aktywowania środowiska:

```powershell
.\.venv\Scripts\python.exe .\LeagueOfLegendsAPP\web_ui.py
```

Na Windows możesz również dwukrotnie kliknąć plik `Uruchom_LoL_Player_Viewer.cmd`. Skrypt zawsze wybierze projektowe środowisko `.venv` i uruchomi nowy interfejs WebView.

W Visual Studio jako interpreter projektu wybierz:

```text
.venv\Scripts\python.exe
```

W Visual Studio plik `web_ui.py` jest ustawiony jako domyślny plik startowy.

### Wersja Windows EXE

Gotowe wydanie `LoLPlayerViewer.exe` jest pojedynczym plikiem i nie wymaga instalowania Pythona ani zależności. Klucz można wkleić bezpośrednio w aplikacji. Opcjonalnie można umieścić `config.json` w tym samym folderze co EXE, aby klucz został wczytany automatycznie.

## Lokalny plik z kluczem API

Skopiuj `config.example.json` jako `config.json`, a następnie wpisz klucz:

```json
{
  "riot_api_key": "RGAPI-TWOJ-KLUCZ"
}
```

`config.json` jest wpisany do `.gitignore` i nie zostanie wysłany do GitHub. Do repozytorium trafia wyłącznie bezpieczny szablon `config.example.json`, który nie zawiera prawdziwego sekretu. Klucz zapisany w JSON pozostaje jawnym tekstem na lokalnym komputerze, dlatego pliku nie należy przesyłać ani udostępniać.

Jeśli aplikacja nie ma jeszcze zapamiętanego, zweryfikowanego klucza, najpierw próbuje wartości z `config.json`, a następnie wartości wpisanej w Ustawieniach.

Po pierwszym udanym połączeniu klucz jest zapisywany lokalnie w `%APPDATA%\LoLPlayerViewer\api_key.json`, podobnie jak lista ulubionych. Jeśli Riot API odrzuci klucz jako wygasły lub nieprawidłowy, aplikacja usuwa zapamiętaną wartość, otwiera Ustawienia i prosi o wklejenie nowego klucza. Ostatni zweryfikowany klucz ma pierwszeństwo przed starszą wartością z `config.json`.

## Klucz Riot API

1. Zaloguj się na [Riot Developer Portal](https://developer.riotgames.com/).
2. Skopiuj klucz zaczynający się od `RGAPI-`.
3. Uruchom LoL Player Viewer.
4. Otwórz **Ustawienia** i wklej klucz w zamaskowane pole **Klucz Riot API**.

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
│   ├── LeagueOfLegendsAPP.py  # starszy interfejs Tkinter (awaryjny)
│   ├── web_ui.py              # most Python-JavaScript i domyślny start
│   ├── web/                   # nowy interfejs HTML/CSS/JavaScript
│   ├── riot_api.py            # komunikacja z Riot API
│   ├── assets.py              # grafiki Data Dragon i cache
│   ├── models.py              # modele danych
│   ├── config.py              # regiony i kolejki
│   ├── storage.py             # lokalny zapis ulubionych
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
- Lista ulubionych zapisuje wyłącznie Riot ID i region w `%APPDATA%\LoLPlayerViewer`.
- Klucz Riot API nigdy nie jest dodawany do pliku ulubionych.
- Jeżeli klucz trafił do publicznego repozytorium, natychmiast wygeneruj nowy w Riot Developer Portal.

## Informacja prawna

LoL Player Viewer nie jest wspierany ani zatwierdzony przez Riot Games i nie odzwierciedla poglądów ani opinii Riot Games ani osób oficjalnie zaangażowanych w produkcję lub zarządzanie właściwościami Riot Games. Riot Games oraz wszystkie powiązane właściwości są znakami towarowymi lub zastrzeżonymi znakami towarowymi Riot Games, Inc.
