@echo off
echo =========================================================
echo  CSIT314 Interior Designer Platform (Atelier Match)
echo =========================================================
echo.
echo Membersihkan proses server lama...
taskkill /F /IM python.exe 2>nul
echo.
echo Membuka browser ke http://127.0.0.1:3001 ...
start http://127.0.0.1:3001
echo.
echo Server aktif di http://127.0.0.1:3001
echo (Tekan Ctrl+C untuk berhenti)
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
