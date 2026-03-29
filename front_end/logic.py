"""
logic.py — Clinical / business logic.
No Streamlit imports here; pure Python so it can be unit-tested independently.
Reads the model from st.session_state when needed (call-site responsibility).
"""

import hashlib
import math
import random


#── Fallback rule-based predictor ────────────────────────────────────────────
def predict(f: dict) -> dict:
    """
    Simple rule-based CTAS predictor used when the ML model is unavailable.
    Returns {"ctas": int, "probabilities": {1..5: float}, "confidence": float}
    """
    sbp, hr, rr, bt = f["SBP"], f["HR"], f["RR"], f["BT"]
    nrs, age        = f["NRS_pain"], f["Age"]
    s = 3
    if sbp < 90:            s -= 2
    elif sbp < 100:         s -= 1
    if hr > 130 or hr < 40: s -= 2
    elif hr > 110:          s -= 1
    if rr > 30 or rr < 8:  s -= 2
    elif rr > 24:           s -= 1
    if bt > 39.5:           s -= 1
    if bt > 41:             s -= 1
    if nrs >= 8:            s -= 1
    if nrs <= 2:            s += 1
    if age >= 80 or age <= 2: s -= 1
    noise = random.choice([-1, 0, 0, 0, 1])
    p     = max(1, min(5, s + noise))
    raw   = [math.exp(-abs(i + 1 - p) * 1.6) * (0.75 + random.random() * 0.5)
             for i in range(5)]
    total = sum(raw)
    pr    = [round(v / total, 3) for v in raw]
    return {
        "ctas":          p,
        "probabilities": {i + 1: pr[i] for i in range(5)},
        "confidence":    pr[p - 1],
    }


def predict_with_model(f: dict, model, threshold_class_1, threshold_class_2) -> dict:
    """
    ML-model predictor — wraps predict_with_all_rules from triage_utils.
    Falls back to rule-based predict() if anything goes wrong.
    """
    try:
        from front_end.triage_utils import (
            predict_with_all_rules,
            obstetric_rule_override,
            clinical_rule_override,
            combined_rule_override,
            clean_text_func,
        )
        result = predict_with_all_rules(
            f, model, threshold_class_1, threshold_class_2,
            obstetric_rule_override, clinical_rule_override,
            combined_rule_override,
        )
        return result
    except Exception:
        return predict(f)


# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Vital-sign warning flags ──────────────────────────────────────────────────
def get_warnings(sbp: float, hr: float, rr: float, bt: float, nrs: int) -> list[str]:
    w = []
    if sbp < 90:  w.append("Hypotension — SBP below 90 mmHg")
    if hr > 120:  w.append("Tachycardia — HR above 120 bpm")
    if hr < 50:   w.append("Bradycardia — HR below 50 bpm")
    if rr > 25:   w.append("Tachypnea — RR above 25 /min")
    if bt > 38.5: w.append("Fever — Temperature above 38.5 °C")
    if bt < 36:   w.append("Hypothermia — Temperature below 36 °C")
    if nrs >= 8:  w.append("Severe pain — NRS score ≥ 8/10")
    return w
