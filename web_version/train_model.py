"""손글씨 숫자(0~9) 인식 모델 학습 스크립트.

scikit-learn 내장 digits 데이터셋(8x8 흑백 숫자 이미지)으로 MLP 분류기를 학습하고
model/digit_model.pkl 로 저장한다. 웹 서버(app.py)는 이 파일을 로드해서 예측에 사용한다.
"""

import pickle
from pathlib import Path

from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_PATH = Path(__file__).parent / "model" / "digit_model.pkl"


def main():
    digits = load_digits()
    X_train, X_test, y_train, y_test = train_test_split(
        digits.data, digits.target, test_size=0.2, random_state=42, stratify=digits.target
    )

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "mlp",
                MLPClassifier(
                    hidden_layer_sizes=(100, 50),
                    max_iter=2000,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    print(f"테스트 정확도: {accuracy:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"모델 저장 완료: {MODEL_PATH}")


if __name__ == "__main__":
    main()
