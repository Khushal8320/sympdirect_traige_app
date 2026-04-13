from src.safety.vitals import VitalSignChecker


class TestVitalSignChecker:
    def test_sbp_low_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": 89})
        assert result is not None
        assert result.ctas_override == 1
        assert "SBP" in result.vital

    def test_sbp_at_boundary_no_trigger(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": 90})
        # SBP=90 is NOT < 90, so should not trigger
        sbp_low = [r for r in [result] if r and r.vital == "SBP" and "Hypotension" in r.reason]
        assert len(sbp_low) == 0

    def test_sbp_high_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": 181})
        assert result is not None
        assert result.ctas_override <= 2

    def test_sbp_high_boundary_no_trigger(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": 180})
        # SBP=180 is NOT > 180
        assert result is None

    def test_hr_low_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"HR": 39})
        assert result is not None
        assert result.ctas_override == 1

    def test_hr_low_boundary(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"HR": 40})
        assert result is None

    def test_hr_high_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"HR": 121})
        assert result is not None
        assert result.ctas_override == 2

    def test_hr_high_boundary(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"HR": 120})
        assert result is None

    def test_rr_high_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"RR": 31})
        assert result is not None
        assert result.ctas_override == 2

    def test_rr_boundary(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"RR": 30})
        assert result is None

    def test_bt_low_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"BT": 35.9})
        assert result is not None
        assert result.ctas_override == 2

    def test_bt_high_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"BT": 39.1})
        assert result is not None

    def test_saturation_low_triggers(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"Saturation": 89})
        assert result is not None
        assert result.ctas_override == 1

    def test_saturation_boundary(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"Saturation": 90})
        assert result is None

    def test_multiple_violations_most_severe_wins(self, thresholds):
        checker = VitalSignChecker(thresholds)
        # SBP<90 = KTAS 1, HR>120 = KTAS 2 → should get KTAS 1
        result = checker.check({"SBP": 80, "HR": 130})
        assert result is not None
        assert result.ctas_override == 1

    def test_missing_vitals_returns_none(self, thresholds):
        checker = VitalSignChecker(thresholds)
        assert checker.check({}) is None
        assert checker.check(None) is None

    def test_none_vital_value_skipped(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": None, "HR": None})
        assert result is None

    def test_non_numeric_vital_skipped(self, thresholds):
        checker = VitalSignChecker(thresholds)
        result = checker.check({"SBP": "invalid", "HR": "abc"})
        assert result is None
