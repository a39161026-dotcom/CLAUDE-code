#!/usr/bin/env bash
# 손글씨 숫자 인식 웹 앱을 한 번에 설치 + 실행합니다.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo "서버를 시작합니다: http://localhost:5000"
python app.py
