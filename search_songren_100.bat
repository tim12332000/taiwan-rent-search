@echo off
setlocal

cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0open_search_app.ps1" -NoBrowser
python -m src.songren_100_case --open

endlocal
