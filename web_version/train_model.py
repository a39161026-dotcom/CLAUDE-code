"""손글씨 숫자(0~9) 인식 모델 학습 스크립트.

두 가지 데이터 소스를 합쳐서 학습한다.

1. sklearn 내장 `digits` 데이터셋 — 실제 사람이 손으로 쓴 숫자를 스캐너로
   읽어들인 데이터라 자연스러운 필기 곡선을 담고 있다. 다만 원본이 8x8
   저해상도라 세부 형태 정보가 적다.
2. 로컬 시스템 폰트로 렌더링한 숫자 — 글씨체는 기계적이지만 크기/위치/
   회전/두께를 자유롭게 다양화할 수 있어 캔버스 입력의 실제 분포(두꺼운
   획, 기울어짐, 중심 이탈)를 흉내내기 좋다.

두 소스 모두 같은 증강 함수(augment_glyph)와 같은 전처리(preprocessing.py)를
거쳐 최종적으로 8x8 벡터가 되므로, 실제 필기 곡선과 캔버스 특유의 다양성을
함께 학습한다. 외부 데이터셋 다운로드가 필요 없어 네트워크가 막힌 환경에서도
재현 가능하다.
"""

import pickle
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from preprocessing import crop_to_bbox, to_model_input

MODEL_PATH = Path(__file__).parent / "model" / "digit_model.pkl"

CANVAS = 200
INK_THRESHOLD = 40
SAMPLES_PER_FONT_DIGIT = 15
AUGMENTATIONS_PER_REAL_SAMPLE = 3

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


def render_font_glyph(font_path: Path, digit: int) -> Image.Image | None:
    """폰트로 숫자를 여백 없이 렌더링해 그 숫자만의 경계 상자로 잘라낸다."""
    size = 160
    font = ImageFont.truetype(str(font_path), size)
    tmp = Image.new("L", (size * 2, size * 2), color=0)
    draw = ImageDraw.Draw(tmp)
    text = str(digit)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if w <= 0 or h <= 0:
        return None
    draw.text((-bbox[0], -bbox[1]), text, fill=255, font=font)
    return tmp.crop((0, 0, w, h))


def real_digit_glyph(image8x8: np.ndarray) -> Image.Image | None:
    """sklearn digits의 8x8 실제 손글씨 샘플을 그 숫자만의 경계 상자로 잘라낸다."""
    arr = (np.clip(image8x8, 0, 16) / 16.0 * 255).astype(np.uint8)
    mask = arr > 0
    if not mask.any():
        return None
    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    return Image.fromarray(arr, mode="L").crop((x0, y0, x1, y1))


def augment_glyph(glyph: Image.Image, rng: random.Random) -> np.ndarray | None:
    """숫자 하나짜리 glyph 이미지를 무작위 크기/위치/회전/굵기로 캔버스에 배치해
    모델 입력 벡터로 변환한다. 폰트 glyph와 실제 손글씨 glyph 양쪽에 똑같이 쓴다."""
    w, h = glyph.size
    if w <= 0 or h <= 0:
        return None

    target_size = rng.randint(100, 160)
    scale = target_size / max(w, h)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    resized = glyph.resize((new_w, new_h), Image.BICUBIC)

    canvas = Image.new("L", (CANVAS, CANVAS), color=0)
    jitter = 15
    x = (CANVAS - new_w) // 2 + rng.randint(-jitter, jitter)
    y = (CANVAS - new_h) // 2 + rng.randint(-jitter, jitter)
    canvas.paste(resized, (x, y))

    angle = rng.uniform(-15, 15)
    canvas = canvas.rotate(angle, resample=Image.BICUBIC, fillcolor=0)

    mask = np.array(canvas) > INK_THRESHOLD
    if not mask.any():
        return None

    # 실제 마우스로 그은 획은 원본보다 두껍거나 얇을 수 있어 일부러 다양화한다.
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


def build_dataset(fonts: list[Path], seed: int = 42):
    rng = random.Random(seed)
    features, labels = [], []

    real_digits = load_digits()
    for image8x8, digit in zip(real_digits.images, real_digits.target):
        glyph = real_digit_glyph(image8x8)
        if glyph is None:
            continue
        for _ in range(AUGMENTATIONS_PER_REAL_SAMPLE):
            vector = augment_glyph(glyph, rng)
            if vector is not None:
                features.append(vector)
                labels.append(int(digit))

    for digit in range(10):
        for font_path in fonts:
            glyph = render_font_glyph(font_path, digit)
            if glyph is None:
                continue
            collected = 0
            attempts = 0
            while collected < SAMPLES_PER_FONT_DIGIT and attempts < SAMPLES_PER_FONT_DIGIT * 3:
                attempts += 1
                vector = augment_glyph(glyph, rng)
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
    print(f"폰트 {len(fonts)}개 + 실제 손글씨(sklearn digits), 샘플 {len(X)}개로 학습")
    print(f"테스트 정확도: {accuracy:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"모델 저장 완료: {MODEL_PATH}")


if __name__ == "__main__":
    main()
