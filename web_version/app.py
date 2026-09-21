"""손글씨 숫자 인식 웹 서버.

브라우저 캔버스에 그린 숫자 이미지를 받아 전처리한 뒤 학습된 모델로 예측 결과를 반환한다.
"""

import base64
import io
import pickle
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, render_template, request
from PIL import Image

import train_model

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model" / "digit_model.pkl"

app = Flask(__name__)

if not MODEL_PATH.exists():
    # 모델 파일이 없으면 최초 실행 시 자동으로 학습해서 생성한다.
    train_model.main()

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


def preprocess_image(data_url: str) -> np.ndarray:
    """캔버스에서 받은 data URL(PNG)을 학습 데이터와 같은 8x8, 0~16 스케일로 변환한다."""
    header, encoded = data_url.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(image_bytes)).convert("L")

    pixels = np.array(image)

    # 그려진 부분(밝은 픽셀)의 경계 상자를 찾아 여백을 잘라내고 숫자를 가운데로 맞춘다.
    coords = np.argwhere(pixels > 20)
    if coords.size > 0:
        y0, x0 = coords.min(axis=0)
        y1, x1 = coords.max(axis=0) + 1
        pad = max((y1 - y0), (x1 - x0)) // 4 + 1
        y0, x0 = max(y0 - pad, 0), max(x0 - pad, 0)
        y1, x1 = min(y1 + pad, pixels.shape[0]), min(x1 + pad, pixels.shape[1])
        image = image.crop((x0, y0, x1, y1))

    # 정사각형 캔버스로 패딩한 뒤 8x8로 축소 (sklearn digits 데이터셋 규격)
    w, h = image.size
    side = max(w, h)
    square = Image.new("L", (side, side), color=0)
    square.paste(image, ((side - w) // 2, (side - h) // 2))
    small = square.resize((8, 8), Image.LANCZOS)

    small_pixels = np.array(small, dtype=np.float64)
    if small_pixels.max() > 0:
        # 다운스케일 시 흐려진 획의 명암을 학습 데이터(0~16, 최댓값 16)와 맞춘다.
        small_pixels = small_pixels / small_pixels.max() * 16.0
    return small_pixels.flatten().reshape(1, -1)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    payload = request.get_json(silent=True) or {}
    data_url = payload.get("image")
    if not data_url:
        return jsonify({"error": "image 데이터가 없습니다."}), 400

    try:
        features = preprocess_image(data_url)
    except Exception:
        return jsonify({"error": "이미지를 처리할 수 없습니다."}), 400

    if not np.any(features):
        return jsonify({"error": "캔버스에 숫자를 먼저 그려주세요."}), 400

    probabilities = model.predict_proba(features)[0]
    prediction = int(np.argmax(probabilities))

    return jsonify(
        {
            "prediction": prediction,
            "probabilities": [round(float(p), 4) for p in probabilities],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
