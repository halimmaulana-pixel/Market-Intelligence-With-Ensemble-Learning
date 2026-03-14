@echo off
echo === SalSa Market — Start Backend ===

:: Matikan semua uvicorn/python yang pakai port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    echo Matikan proses lama (PID %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

:: Tunggu sebentar
timeout /t 2 /nobreak >nul

:: Jalankan backend
cd /d D:\kimi\Salsa\salsa-market\backend
echo Menjalankan backend di http://localhost:8001
echo Tekan Ctrl+C untuk berhenti.
echo.
python -X utf8 -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
