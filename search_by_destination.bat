@echo off
setlocal

cd /d "%~dp0"
set /p DEST=請輸入目的地地址: 
if "%DEST%"=="" (
  echo 未輸入目的地，已取消。
  exit /b 1
)

python -m src.smart_search --destination-address "%DEST%" --open

endlocal
