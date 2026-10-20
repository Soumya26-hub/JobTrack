@echo off
REM Starts JobTrack so a phone on the same Wi-Fi can open it.
cd /d "%~dp0"
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate
    pip install -r backend\requirements.txt
) else (
    call venv\Scripts\activate
)
echo.
echo On your phone, open http://YOUR-LAPTOP-IP:8000
echo Your laptop's IP address is the "IPv4 Address" below:
ipconfig | findstr /i "IPv4"
echo.
uvicorn backend.main:app --host 0.0.0.0 --port 8000
