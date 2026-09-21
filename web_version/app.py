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
from scipy import ndimage

import train_model
from preprocessing import crop_to_bbox, to_model_input

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model" / "digit_model.pkl"

app = Flask(__name__)

if not MODEL_PATH.exists():
    # 모델 파일이 없으면 최초 실행 시 자동으로 학습해서 생성한다.
    train_model.main()

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


MIN_COMPONENT_PIXELS = 15  # 이보다 작은 얼룩은 노이즈로 보고 무시한다.
GAP_DILATION_ITERATIONS = 10  # 이 정도 떨어진 획은 같은 숫자로, 더 멀면 다른 숫자로 취급한다.


def segment_digits(data_url: str) -> list[np.ndarray]:
    """캔버스 이미지에서 숫자별로 떨어진 획을 찾아 왼쪽부터 순서대로 모델 입력 벡터 리스트로 변환한다."""
    header, encoded = data_url.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(image_bytes)).convert("L")

    mask = np.array(image) > 20
    if not mask.any():
        return []

    # 같은 숫자 안에서 떨어진 획(예: '4', '5')은 이어붙이되, 서로 다른 숫자는 분리되도록
    # 살짝 팽창시킨 뒤 연결된 영역을 하나의 숫자로 묶는다.
    dilated = ndimage.binary_dilation(mask, iterations=GAP_DILATION_ITERATIONS)
    labeled, num_components = ndimage.label(dilated)

    components = []
    for label_id in range(1, num_components + 1):
        component_mask = mask & (labeled == label_id)
        if component_mask.sum() < MIN_COMPONENT_PIXELS:
            continue
        cropped, left_x = crop_to_bbox(component_mask, image)
        components.append((left_x, to_model_input(cropped)))

    components.sort(key=lambda c: c[0])
    return [features for _, features in components]


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
        digit_features = segment_digits(data_url)
    except Exception:
        return jsonify({"error": "이미지를 처리할 수 없습니다."}), 400

    if not digit_features:
        return jsonify({"error": "캔버스에 숫자를 먼저 그려주세요."}), 400

    digits = []
    for features in digit_features:
        probabilities = model.predict_proba(features.reshape(1, -1))[0]
        digits.append(
            {
                "digit": int(np.argmax(probabilities)),
                "confidence": round(float(np.max(probabilities)), 4),
            }
        )

    prediction = "".join(str(d["digit"]) for d in digits)

    return jsonify({"prediction": prediction, "digits": digits})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
