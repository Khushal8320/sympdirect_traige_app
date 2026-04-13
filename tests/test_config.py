import json
import os
import tempfile

import pytest

from src.safety.config import load_config, validate_config


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "safety_rules.json")


class TestLoadConfig:
    def test_loads_valid_config(self):
        config = load_config(CONFIG_PATH)
        assert "rules" in config
        assert "vital_thresholds" in config
        assert "symptom_lexicon" in config

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_malformed_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            with pytest.raises(json.JSONDecodeError):
                load_config(f.name)
        os.unlink(f.name)


class TestValidateConfig:
    def test_valid_config_no_errors(self):
        config = load_config(CONFIG_PATH)
        errors = validate_config(config)
        assert errors == []

    def test_missing_rules_key(self):
        errors = validate_config({"vital_thresholds": [], "symptom_lexicon": {}})
        assert any("rules" in e for e in errors)

    def test_missing_vital_thresholds(self):
        errors = validate_config({"rules": [], "symptom_lexicon": {}})
        assert any("vital_thresholds" in e for e in errors)

    def test_duplicate_rule_ids(self):
        config = {
            "rules": [
                {"id": "RED001", "pattern": {}, "ctas_override": 1, "message": "a"},
                {"id": "RED001", "pattern": {}, "ctas_override": 1, "message": "b"},
            ],
            "vital_thresholds": [],
            "symptom_lexicon": {},
        }
        errors = validate_config(config)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_ctas_override(self):
        config = {
            "rules": [
                {"id": "R1", "pattern": {}, "ctas_override": 6, "message": "bad"},
            ],
            "vital_thresholds": [],
            "symptom_lexicon": {},
        }
        errors = validate_config(config)
        assert any("ctas_override" in e for e in errors)

    def test_unknown_symptom_token_in_rule(self):
        config = {
            "rules": [
                {
                    "id": "R1",
                    "pattern": {"requires_all": ["nonexistent_token"]},
                    "ctas_override": 1,
                    "message": "test",
                },
            ],
            "vital_thresholds": [],
            "symptom_lexicon": {},
        }
        errors = validate_config(config)
        assert any("unknown symptom token" in e for e in errors)

    def test_missing_rule_fields(self):
        config = {
            "rules": [{"id": "R1"}],
            "vital_thresholds": [],
            "symptom_lexicon": {},
        }
        errors = validate_config(config)
        assert any("missing field" in e for e in errors)

    def test_invalid_vital_condition(self):
        config = {
            "rules": [],
            "vital_thresholds": [
                {"vital": "SBP", "condition": "eq", "value": 90, "ctas_override": 1, "reason": "x"}
            ],
            "symptom_lexicon": {},
        }
        errors = validate_config(config)
        assert any("condition" in e for e in errors)
