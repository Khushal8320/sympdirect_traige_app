import os

import joblib
import pandas as pd

from src.safety.engine import SafetyEngine

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "safety_rules.json")
DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "best_triage_model.pkl")


def predict_triage(
    chief_complaint: str,
    vitals: dict,
    pain_score: float | None = None,
    age: float | None = None,
    sex: str | None = None,
    ktas_rn: str | None = None,
    model_path: str = DEFAULT_MODEL,
    config_path: str = DEFAULT_CONFIG,
) -> dict:
    """Run safety layer first, then ML model if no override triggered.

    Returns dict with keys: ktas, source, safety_result, model_prediction.
    """
    # Run safety engine
    engine = SafetyEngine(config_path)
    safety_result = engine.evaluate(chief_complaint, vitals, pain_score, age)

    if safety_result is not None:
        return {
            "ktas": safety_result.override_ktas,
            "source": "safety_override",
            "safety_result": safety_result,
            "model_prediction": None,
        }

    # Fall through to ML model
    model_prediction = _run_model(
        model_path, chief_complaint, vitals, pain_score, age, sex, ktas_rn
    )

    return {
        "ktas": model_prediction,
        "source": "model",
        "safety_result": None,
        "model_prediction": model_prediction,
    }


def _run_model(
    model_path: str,
    chief_complaint: str,
    vitals: dict,
    pain_score: float | None,
    age: float | None,
    sex: str | None,
    ktas_rn: str | None,
) -> int:
    """Load model bundle and predict KTAS score.

    The pkl contains: model_name, preprocessor, classifier, label_shift, features.
    """
    bundle = joblib.load(model_path)

    preprocessor = bundle["preprocessor"]
    classifier = bundle["classifier"]
    label_shift = bundle.get("label_shift", 0)
    feature_info = bundle["features"]

    row = {
        feature_info["text"]: chief_complaint or "",
    }
    for col in feature_info.get("numerical", []):
        if col == "NRS_pain":
            row[col] = pain_score
        elif col == "Age":
            row[col] = age
        else:
            row[col] = vitals.get(col)
    for col in feature_info.get("categorical", []):
        if col == "Sex":
            row[col] = sex
        elif col == "KTAS_RN":
            row[col] = ktas_rn
        else:
            row[col] = None

    df = pd.DataFrame([row])
    X = preprocessor.transform(df)
    prediction = classifier.predict(X)
    return int(prediction[0]) + label_shift
