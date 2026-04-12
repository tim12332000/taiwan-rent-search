@echo off
setlocal

cd /d "%~dp0"
wscript.exe "%~dp0search_by_destination.vbs"

endlocal
