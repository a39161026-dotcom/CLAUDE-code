@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
    set "PY=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PY=py"
    ) else (
        echo [ERROR] Python이 설치되어 있지 않거나 PATH에 등록되어 있지 않습니다.
        echo https://www.python.org/downloads/ 에서 설치할 때 "Add python.exe to PATH"를 꼭 체크하세요.
        pause
        exit /b 1
    )
)

if not exist .venv (
    %PY% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt

echo 서버를 시작합니다: http://localhost:5000
python app.py
pause
