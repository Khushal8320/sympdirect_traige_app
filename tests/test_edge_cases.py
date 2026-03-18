from src.safety.engine import SafetyEngine


class TestEdgeCases:
    def test_empty_complaint_empty_vitals(self, engine):
        result = engine.evaluate("", {})
        assert result is None

    def test_none_complaint_none_vitals(self, engine):
        result = engine.evaluate(None, None)
        assert result is None

    def test_none_everything(self, engine):
        result = engine.evaluate(None, None, pain_score=None, age=None)
        assert result is None

    def test_non_numeric_vital_values(self, engine):
        result = engine.evaluate("headache", {"SBP": "invalid", "HR": "abc"})
        assert result is None

    def test_very_long_text(self, engine):
        long_text = "mild headache " * 10000
        result = engine.evaluate(long_text, {})
        assert result is None

    def test_unicode_characters(self, engine):
        result = engine.evaluate("douleur thoracique café résumé", {})
        # No crash expected
        assert result is None or isinstance(result.override_ktas, int)

    def test_special_characters(self, engine):
        # chest pain + SOB with special chars should still trigger RED001
        result = engine.evaluate("chest pain!!! shortness of breath @#$%", {})
        assert result is not None
        assert result.rule_id == "RED001"

    def test_pain_exact_float_boundary_triggers(self, engine):
        result = engine.evaluate("chest pain", {}, pain_score=9.0)
        assert result is not None
        assert result.rule_id == "RED007"

    def test_pain_just_below_boundary(self, engine):
        result = engine.evaluate("chest pain", {}, pain_score=8.99)
        if result:
            assert result.rule_id != "RED007"

    def test_age_exact_boundary(self, engine):
        result = engine.evaluate("fever", {}, age=3.0)
        assert result is not None
        assert result.rule_id == "RED008"

    def test_age_just_above_boundary(self, engine):
        result = engine.evaluate("fever", {}, age=3.01)
        if result:
            assert result.rule_id != "RED008"

    def test_integer_type_input(self, engine):
        result = engine.evaluate("chest pain shortness of breath", {"SBP": 120, "HR": 80})
        assert result is not None
        assert result.rule_id == "RED001"
