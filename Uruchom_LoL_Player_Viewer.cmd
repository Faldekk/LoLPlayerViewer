@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Brak lokalnego srodowiska Python .venv.
    echo Utworz je i zainstaluj zaleznosci zgodnie z README.md.
    pause
    exit /b 1
)

start "LoL Player Viewer" ".venv\Scripts\pythonw.exe" ".\LeagueOfLegendsAPP\web_ui.py"
