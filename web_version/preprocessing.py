"""캔버스 이미지를 모델 입력(8x8, 0~16 스케일)으로 바꾸는 공용 전처리 함수.

학습(train_model.py)과 서비스(app.py) 양쪽에서 반드시 같은 함수를 써야
학습 때 본 분포와 실제 추론 입력의 분포가 어긋나지 않는다.
"""

import numpy as np
from PIL import Image


def crop_to_bbox(mask: np.ndarray, image: Image.Image) -> tuple[Image.Image, int]:
    """mask가 True인 영역의 경계 상자에 축별로 비례한 여백을 두고 잘라낸다.

    가로/세로 여백을 각 축 크기에 비례해 따로 계산해야 '1'처럼 가늘고 긴
    획이 한쪽으로 쏠려 잘리는 문제가 생기지 않는다.
    반환값은 (잘라낸 이미지, 원본에서의 왼쪽 x좌표).
    """
    coords = np.argwhere(mask)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1
    pad_y = (y1 - y0) // 4 + 1
    pad_x = (x1 - x0) // 4 + 1
    y0, x0 = max(y0 - pad_y, 0), max(x0 - pad_x, 0)
    y1, x1 = min(y1 + pad_y, image.height), min(x1 + pad_x, image.width)
    return image.crop((x0, y0, x1, y1)), x0


def to_model_input(cropped: Image.Image) -> np.ndarray:
    """잘라낸 숫자 이미지를 정사각형으로 패딩한 뒤 8x8로 축소하고 명암을 정규화한다."""
    w, h = cropped.size
    side = max(w, h)
    square = Image.new("L", (side, side), color=0)
    square.paste(cropped, ((side - w) // 2, (side - h) // 2))
    small = square.resize((8, 8), Image.LANCZOS)

    small_pixels = np.array(small, dtype=np.float64)
    if small_pixels.max() > 0:
        # 다운스케일 시 흐려진 획의 명암을 학습 데이터(0~16, 최댓값 16)와 맞춘다.
        small_pixels = small_pixels / small_pixels.max() * 16.0
    return small_pixels.flatten()
