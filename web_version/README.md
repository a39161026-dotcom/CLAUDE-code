# 손글씨 숫자 인식 (웹 버전)

브라우저 캔버스에 마우스(또는 터치)로 숫자(0~9)를 그리면 Flask 서버가 학습된 모델로 예측 결과를 반환합니다.

## 실행 방법

```bash
cd web_version
pip install -r requirements.txt

# 모델 학습 (최초 1회, model/digit_model.pkl 생성)
python train_model.py

# 서버 실행
python app.py
```

브라우저에서 `http://localhost:5000` 접속 후 캔버스에 숫자를 그리고 "예측하기"를 누르세요.

## 구조

- `train_model.py` — scikit-learn `digits` 데이터셋(8x8 숫자 이미지)으로 MLP 분류기를 학습해 `model/digit_model.pkl`로 저장
- `app.py` — Flask 서버. `/` 는 캔버스 페이지, `/predict` 는 캔버스 이미지를 받아 예측 결과를 JSON으로 반환
- `templates/index.html`, `static/script.js`, `static/style.css` — 캔버스 UI 및 예측 요청 처리
