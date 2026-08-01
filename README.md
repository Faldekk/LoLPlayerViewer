# LoL Player Viewer

Desktopowa aplikacja w Pythonie pokazująca profil, rangi, 30 ostatnich meczów gracza League of Legends oraz wykres KDA z gier rankingowych.

## Uruchomienie

1. Pobierz klucz deweloperski na stronie [Riot Developer Portal](https://developer.riotgames.com/).
2. Zainstaluj bibliotekę do wykresów:

   ```powershell
   python -m pip install -r .\requirements.txt
   ```

3. Uruchom aplikację:

   ```powershell
   python .\LeagueOfLegendsAPP\LeagueOfLegendsAPP.py
   ```

Po uruchomieniu wklej klucz w zamaskowane pole **Klucz Riot API**. Klucz pozostaje tylko w pamięci programu i nie jest zapisywany na dysku. Opcjonalnie aplikacja nadal odczytuje zmienną środowiskową `RIOT_API_KEY`. Nie wpisuj klucza bezpośrednio do kodu i nie publikuj go w repozytorium. Klucze deweloperskie Riot zwykle wygasają po 24 godzinach.

## Obsługa

Wpisz pełny Riot ID, np. `NazwaGracza#EUNE`, wybierz region konta i kliknij **Wyszukaj**. Zakładka **Historia meczów** pokazuje wszystkie pobrane gry, a **Analiza ranked** prezentuje KDA i wyniki meczów Solo/Duo oraz Flex.
