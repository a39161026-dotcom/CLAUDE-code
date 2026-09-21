# 손글씨 숫자 인식 (웹 버전)

브라우저 캔버스에 마우스(또는 터치)로 숫자(0~9)를 그리면 Flask 서버가 학습된 모델로 예측 결과를 반환합니다.

## 바로 실행하기

`web_version` 폴더에 학습된 모델(`model/digit_model.pkl`)이 이미 포함되어 있어서
가상환경 생성 + 의존성 설치 + 서버 실행을 한 번에 해주는 스크립트만 실행하면 됩니다.

**macOS / Linux**
```bash
cd web_version
./run.sh
```

**Windows**
```bat
cd web_version
run.bat
```

실행 후 브라우저에서 `http://localhost:5000` 접속 → 캔버스에 숫자를 그리고 "예측하기" 클릭.

### 수동으로 실행하려면

```bash
cd web_version
pip install -r requirements.txt
python app.py   # model/digit_model.pkl 이 없으면 첫 실행 시 자동으로 학습해서 생성함
```

모델을 새로 학습하고 싶다면 `python train_model.py` 를 직접 실행하세요.

## 구조

- `train_model.py` — scikit-learn `digits` 데이터셋(8x8 숫자 이미지)으로 MLP 분류기를 학습해 `model/digit_model.pkl`로 저장
- `app.py` — Flask 서버. `/` 는 캔버스 페이지, `/predict` 는 캔버스 이미지를 받아 예측 결과를 JSON으로 반환
- `templates/index.html`, `static/script.js`, `static/style.css` — 캔버스 UI 및 예측 요청 처리
