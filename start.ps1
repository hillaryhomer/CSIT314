Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host " CSIT314 Interior Designer Platform (Atelier Match)" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Membersihkan proses server lama..." -ForegroundColor Yellow
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Membuka browser ke http://127.0.0.1:3002 ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:3002"
Write-Host ""
Write-Host "Server aktif di http://127.0.0.1:3002" -ForegroundColor Yellow
Write-Host "(Tekan Ctrl+C untuk berhenti)" -ForegroundColor Gray
Write-Host ""

if (Test-Path ".\.venv\Scripts\python.exe") {
    & ".\.venv\Scripts\python.exe" app.py
} else {
    python app.py
}
