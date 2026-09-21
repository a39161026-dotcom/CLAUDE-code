@echo off
REM 손글씨 숫자 인식 웹 앱을 한 번에 설치 + 실행합니다.
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo 서버를 시작합니다: http://localhost:5000
python app.py
