"""손글씨 숫자(0~9) 인식 모델 학습 스크립트.

시스템에 설치된 여러 폰트로 숫자를 렌더링하고 회전/위치/굵기를 무작위로
바꿔가며 합성 학습 데이터를 만든다. 실제 캔버스 입력과 동일한 전처리
(preprocessing.py)를 거쳐 8x8 벡터로 변환한 뒤 MLP 분류기를 학습한다.

외부 데이터셋(MNIST 등)을 내려받지 않고 로컬 폰트만으로 학습 데이터를
생성하기 때문에 네트워크 접근이 막힌 환경에서도 재현 가능하다. 폰트로
렌더링한 숫자와 브라우저 캔버스에서 손으로 그린 숫자는 완전히 같지는
않지만, sklearn의 8x8 스캐너 데이터셋보다 캔버스 입력의 실제 분포
(두꺼운 획, 기울어짐, 중심 이탈)에 훨씬 가깝다.
"""

import pickle
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from preprocessing import crop_to_bbox, to_model_input

MODEL_PATH = Path(__file__).parent / "model" / "digit_model.pkl"

CANVAS = 200
SAMPLES_PER_FONT_DIGIT = 40
INK_THRESHOLD = 40

FONT_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/freefont"),
]


def find_fonts() -> list[Path]:
    fonts = []
    for directory in FONT_DIRS:
        if directory.exists():
            fonts.extend(sorted(directory.glob("*.ttf")))
    return fonts


def render_sample(font_path: Path, digit: int, rng: random.Random) -> np.ndarray | None:
    """폰트로 숫자 하나를 무작위 크기/위치/회전/굵기로 렌더링해 모델 입력 벡터로 변환한다."""
    size = rng.randint(90, 150)
    font = ImageFont.truetype(str(font_path), size)
    img = Image.new("L", (CANVAS, CANVAS), color=0)
    draw = ImageDraw.Draw(img)
    text = str(digit)

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    jitter = 12
    x = (CANVAS - w) // 2 - bbox[0] + rng.randint(-jitter, jitter)
    y = (CANVAS - h) // 2 - bbox[1] + rng.randint(-jitter, jitter)
    draw.text((x, y), text, fill=255, font=font)

    angle = rng.uniform(-15, 15)
    img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=0)

    mask = np.array(img) > INK_THRESHOLD
    if not mask.any():
        return None

    # 실제 마우스로 그은 획은 폰트보다 두껍거나 얇을 수 있어 일부러 다양화한다.
    thickness = rng.choice([-1, 0, 0, 0, 1, 1, 2])
    if thickness > 0:
        mask = ndimage.binary_dilation(mask, iterations=thickness)
    elif thickness < 0:
        eroded = ndimage.binary_erosion(mask, iterations=-thickness)
        if eroded.any():
            mask = eroded

    arr = np.where(mask, 255, 0).astype(np.uint8)
    image = Image.fromarray(arr, mode="L")

    cropped, _ = crop_to_bbox(mask, image)
    return to_model_input(cropped)


def build_dataset(fonts: list[Path], samples_per_combo: int = SAMPLES_PER_FONT_DIGIT, seed: int = 42):
    rng = random.Random(seed)
    features, labels = [], []
    for digit in range(10):
        for font_path in fonts:
            collected = 0
            attempts = 0
            while collected < samples_per_combo and attempts < samples_per_combo * 3:
                attempts += 1
                vector = render_sample(font_path, digit, rng)
                if vector is None:
                    continue
                features.append(vector)
                labels.append(digit)
                collected += 1
    return np.array(features), np.array(labels)


def main():
    fonts = find_fonts()
    if not fonts:
        raise RuntimeError("학습용 폰트를 찾지 못했습니다 (dejavu/liberation/freefont).")

    X, y = build_dataset(fonts)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(128, 64),
                    max_iter=3000,
                    random_state=42,
                    early_stopping=True,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    print(f"폰트 {len(fonts)}개, 샘플 {len(X)}개로 학습")
    print(f"테스트 정확도: {accuracy:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"모델 저장 완료: {MODEL_PATH}")


if __name__ == "__main__":
    main()
