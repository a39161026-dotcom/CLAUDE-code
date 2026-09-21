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
from preprocessing import crop_to_bbox, to_model_input

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model" / "digit_model.pkl"

app = Flask(__name__)

if not MODEL_PATH.exists():
    # 모델 파일이 없으면 최초 실행 시 자동으로 학습해서 생성한다.
    train_model.main()

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


MIN_INK_PIXELS = 15  # 이보다 잉크가 적은 조각은 노이즈로 보고 무시한다.
MIN_GAP_WIDTH = 18  # 이보다 넓게 완전히 빈 세로줄이 있어야 다른 숫자로 취급한다.


def _find_digit_column_ranges(col_has_ink: np.ndarray, min_gap: int) -> list[tuple[int, int]]:
    """세로 방향으로 잉크가 하나도 없는 폭이 min_gap 이상인 구간만 숫자 경계로 본다.

    '8'의 위아래 원, '5'의 가로선+곡선처럼 펜을 뗐다 이어그린 한 숫자 안의 획은
    보통 x축 범위가 겹치기 때문에(세로로만 떨어져 있음) 이 기준으로는 갈라지지
    않고, 나란히 그린 서로 다른 숫자만 갈라진다.
    """
    width = len(col_has_ink)
    ranges = []
    seg_start = None
    col = 0
    while col < width:
        if col_has_ink[col]:
            if seg_start is None:
                seg_start = col
            col += 1
            continue

        gap_start = col
        while col < width and not col_has_ink[col]:
            col += 1
        if col - gap_start >= min_gap and seg_start is not None:
            ranges.append((seg_start, gap_start))
            seg_start = None

    if seg_start is not None:
        ranges.append((seg_start, width))
    return ranges


def segment_digits(data_url: str) -> list[np.ndarray]:
    """캔버스 이미지에서 숫자별로 나뉜 구간을 찾아 왼쪽부터 순서대로 모델 입력 벡터 리스트로 변환한다."""
    header, encoded = data_url.split(",", 1)
    image_bytes = base64.b64decode(encoded)
    image = Image.open(io.BytesIO(image_bytes)).convert("L")

    mask = np.array(image) > 20
    if not mask.any():
        return []

    col_has_ink = mask.any(axis=0)
    column_ranges = _find_digit_column_ranges(col_has_ink, MIN_GAP_WIDTH)

    digit_vectors = []
    for x0, x1 in column_ranges:
        segment_mask = np.zeros_like(mask)
        segment_mask[:, x0:x1] = mask[:, x0:x1]
        if segment_mask.sum() < MIN_INK_PIXELS:
            continue
        cropped, _ = crop_to_bbox(segment_mask, image)
        digit_vectors.append(to_model_input(cropped))

    return digit_vectors


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
