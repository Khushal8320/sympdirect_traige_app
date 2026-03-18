from src.safety.engine import SafetyEngine


class TestSafetyEngineRules:
    """Test each RED rule individually."""

    def test_red001_chest_pain_and_sob(self, engine):
        result = engine.evaluate("chest pain with shortness of breath", {})
        assert result is not None
        assert result.rule_id == "RED001"
        assert result.override_ktas == 1

    def test_red001_partial_no_trigger(self, engine):
        # Only chest pain without SOB should not trigger RED001
        result = engine.evaluate("chest pain only", {})
        # May still trigger RED007 if pain_score provided, but without it, no RED001
        if result:
            assert result.rule_id != "RED001"

    def test_red002_stroke(self, engine):
        result = engine.evaluate("suspected stroke with motor weakness", {})
        assert result is not None
        assert result.override_ktas == 1

    def test_red002_mental_change(self, engine):
        result = engine.evaluate("mental change and confusion", {})
        assert result is not None
        assert result.rule_id == "RED002"
        assert result.override_ktas == 1

    def test_red002_unresponsive(self, engine):
        result = engine.evaluate("patient is unresponsive", {})
        assert result is not None
        assert result.override_ktas == 1

    def test_red003_seizure(self, engine):
        result = engine.evaluate("Seizure Like Activity", {})
        assert result is not None
        assert result.rule_id == "RED003"
        assert result.override_ktas == 2

    def test_red003_involuntary_movement(self, engine):
        result = engine.evaluate("involuntary movt and twitching", {})
        assert result is not None
        assert result.rule_id == "RED003"

    def test_red004_respiratory_distress(self, engine):
        result = engine.evaluate("shortness of breath with stridor", {})
        assert result is not None
        assert result.rule_id == "RED004"
        assert result.override_ktas == 1

    def test_red004_partial_no_trigger(self, engine):
        # SOB alone should not trigger RED004 (needs cyanosis/choking/stridor too)
        result = engine.evaluate("shortness of breath", {})
        if result:
            assert result.rule_id != "RED004"

    def test_red005_hemorrhage(self, engine):
        result = engine.evaluate("massive hemorrhage from wound", {})
        assert result is not None
        assert result.rule_id == "RED005"
        assert result.override_ktas == 1

    def test_red005_hematochezia(self, engine):
        result = engine.evaluate("hematochezia and rectal bleeding", {})
        assert result is not None
        assert result.rule_id == "RED005"

    def test_red006_anaphylaxis_with_swelling(self, engine):
        result = engine.evaluate("anaphylaxis with facial swelling", {})
        assert result is not None
        assert result.rule_id == "RED006"
        assert result.override_ktas == 1

    def test_red006_no_swelling_no_trigger(self, engine):
        # Anaphylaxis without swelling should not trigger RED006
        result = engine.evaluate("anaphylaxis", {})
        if result:
            assert result.rule_id != "RED006"

    def test_red007_severe_chest_pain(self, engine):
        result = engine.evaluate("chest pain", {}, pain_score=9)
        assert result is not None
        assert result.rule_id == "RED007"
        assert result.override_ktas == 1

    def test_red007_pain_below_threshold(self, engine):
        result = engine.evaluate("chest pain", {}, pain_score=8)
        if result:
            assert result.rule_id != "RED007"

    def test_red007_pain_none_no_trigger(self, engine):
        result = engine.evaluate("chest pain", {}, pain_score=None)
        if result:
            assert result.rule_id != "RED007"

    def test_red008_pediatric_fever(self, engine):
        result = engine.evaluate("fever", {}, age=2)
        assert result is not None
        assert result.rule_id == "RED008"
        assert result.override_ktas == 2

    def test_red008_age_boundary_triggers(self, engine):
        result = engine.evaluate("fever", {}, age=3)
        assert result is not None
        assert result.rule_id == "RED008"

    def test_red008_age_above_no_trigger(self, engine):
        result = engine.evaluate("fever", {}, age=4)
        if result:
            assert result.rule_id != "RED008"

    def test_red009_syncope_with_chest_pain(self, engine):
        result = engine.evaluate("syncope with chest pain", {})
        assert result is not None
        assert result.rule_id in ("RED001", "RED009")
        assert result.override_ktas == 1

    def test_red010_severe_burn(self, engine):
        result = engine.evaluate("severe burn with inhalation injury", {})
        assert result is not None
        assert result.rule_id == "RED010"
        assert result.override_ktas == 1


class TestSafetyEnginePriority:
    def test_multiple_rules_lowest_ktas_wins(self, engine):
        # Triggers RED003 (KTAS 2) and RED002 (KTAS 1) - should get KTAS 1
        result = engine.evaluate("seizure with mental change and confusion", {})
        assert result is not None
        assert result.override_ktas == 1

    def test_no_rules_match_returns_none(self, engine):
        result = engine.evaluate("mild headache", {})
        assert result is None

    def test_vital_override_combined_with_text(self, engine):
        result = engine.evaluate("seizure", {"SBP": 80})
        assert result is not None
        assert result.override_ktas == 1  # SBP<90 is KTAS 1

    def test_empty_complaint_vital_only(self, engine):
        result = engine.evaluate("", {"SBP": 80})
        assert result is not None
        assert result.override_ktas == 1
