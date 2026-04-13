import os

import pytest

from src.predict import predict_triage

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "safety_rules.json")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "best_triage_model.pkl")

has_model = os.path.exists(MODEL_PATH)


class TestIntegration:
    def test_safety_override_patient(self):
        result = predict_triage(
            chief_complaint="chest pain with shortness of breath",
            vitals={"SBP": 80, "HR": 130},
            pain_score=9,
            age=55,
            config_path=CONFIG_PATH,
        )
        assert result["source"] == "safety_override"
        assert result["ktas"] == 1
        assert result["safety_result"] is not None

    def test_result_structure(self):
        result = predict_triage(
            chief_complaint="chest pain shortness of breath",
            vitals={},
            config_path=CONFIG_PATH,
        )
        assert "ktas" in result
        assert "source" in result
        assert "safety_result" in result
        assert "model_prediction" in result

    def test_safety_override_vitals_only(self):
        result = predict_triage(
            chief_complaint="mild headache",
            vitals={"SBP": 70},
            config_path=CONFIG_PATH,
        )
        assert result["source"] == "safety_override"
        assert result["ktas"] == 1

    @pytest.mark.skipif(not has_model, reason="Model .pkl not available")
    def test_model_prediction_returned(self):
        result = predict_triage(
            chief_complaint="mild headache",
            vitals={"SBP": 120, "HR": 80, "RR": 16, "BT": 37.0, "Saturation": 98},
            pain_score=3,
            age=30,
            config_path=CONFIG_PATH,
            model_path=MODEL_PATH,
        )
        assert result["source"] == "model"
        assert result["model_prediction"] is not None
        assert 1 <= result["ktas"] <= 5

    @pytest.mark.skipif(not has_model, reason="Model .pkl not available")
    def test_model_prediction_structure(self):
        result = predict_triage(
            chief_complaint="minor cut on finger",
            vitals={"SBP": 120, "HR": 75, "RR": 14, "BT": 36.8, "Saturation": 99},
            pain_score=2,
            age=25,
            config_path=CONFIG_PATH,
            model_path=MODEL_PATH,
        )
        assert isinstance(result["ktas"], int)
        assert result["safety_result"] is None

    def test_safety_takes_precedence_over_model(self):
        result = predict_triage(
            chief_complaint="patient is unresponsive",
            vitals={"SBP": 60},
            config_path=CONFIG_PATH,
        )
        assert result["source"] == "safety_override"
        assert result["ktas"] == 1
