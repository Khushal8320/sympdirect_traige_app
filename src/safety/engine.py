import logging
from dataclasses import dataclass, field

from src.safety.config import load_config, validate_config
from src.safety.symptoms import extract_symptoms
from src.safety.vitals import VitalSignChecker

logger = logging.getLogger(__name__)


@dataclass
class SafetyResult:
    """Result of safety engine evaluation."""
    override_ktas: int
    rule_id: str
    reason: str
    message: str
    triggered_symptoms: set[str] = field(default_factory=set)


class SafetyEngine:
    """Rule-based safety engine that evaluates clinical red flags.

    Sits in front of the ML model and auto-escalates life-threatening patterns.
    """

    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        errors = validate_config(self.config)
        if errors:
            raise ValueError(f"Invalid safety config: {errors}")
        self.rules = self.config["rules"]
        self.lexicon = self.config["symptom_lexicon"]
        self.vital_checker = VitalSignChecker(self.config["vital_thresholds"])
        self.fail_mode = self.config.get("fail_mode", "escalate")

    def evaluate(
        self,
        chief_complaint: str | None,
        vitals: dict | None,
        pain_score: float | None = None,
        age: float | None = None,
    ) -> SafetyResult | None:
        """Evaluate patient data against all safety rules and vital thresholds.

        Returns the most severe SafetyResult (lowest KTAS override), or None.
        """
        try:
            return self._evaluate_internal(chief_complaint, vitals or {}, pain_score, age)
        except Exception:
            logger.exception("Safety engine evaluation error")
            if self.fail_mode == "escalate":
                return SafetyResult(
                    override_ktas=1,
                    rule_id="FAIL_SAFE",
                    reason="Safety engine error - escalating as precaution",
                    message="System error during safety evaluation; escalating to highest priority",
                )
            return None

    def _evaluate_internal(
        self,
        chief_complaint: str | None,
        vitals: dict,
        pain_score: float | None,
        age: float | None,
    ) -> SafetyResult | None:
        symptoms = extract_symptoms(chief_complaint, self.lexicon)
        best: SafetyResult | None = None

        # Evaluate symptom/pattern rules
        for rule in self.rules:
            result = self._check_rule(rule, symptoms, pain_score, age)
            if result and (best is None or result.override_ktas < best.override_ktas):
                best = result

        # Evaluate vital sign thresholds
        violation = self.vital_checker.check(vitals)
        if violation:
            vital_result = SafetyResult(
                override_ktas=violation.ctas_override,
                rule_id=f"VITAL_{violation.vital}",
                reason=violation.reason,
                message=violation.reason,
            )
            if best is None or vital_result.override_ktas < best.override_ktas:
                best = vital_result

        return best

    def _check_rule(
        self,
        rule: dict,
        symptoms: set[str],
        pain_score: float | None,
        age: float | None,
    ) -> SafetyResult | None:
        pattern = rule["pattern"]

        # Check requires_all: every listed symptom must be present
        requires_all = pattern.get("requires_all", [])
        if requires_all:
            if not all(s in symptoms for s in requires_all):
                return None

        # Check requires_any: at least one must be present
        requires_any = pattern.get("requires_any", [])
        if requires_any:
            if not any(s in symptoms for s in requires_any):
                return None

        # If rule has no symptom requirements at all, don't fire on nothing
        if not requires_all and not requires_any:
            return None

        # Check pain_min threshold
        pain_min = pattern.get("pain_min")
        if pain_min is not None:
            if pain_score is None or pain_score < pain_min:
                return None

        # Check age_max threshold
        age_max = pattern.get("age_max")
        if age_max is not None:
            if age is None or age > age_max:
                return None

        # Check severity_min: the severity token must be in extracted symptoms
        severity_min = pattern.get("severity_min")
        if severity_min is not None:
            if severity_min not in symptoms:
                return None

        return SafetyResult(
            override_ktas=rule["ctas_override"],
            rule_id=rule["id"],
            reason=rule.get("name", rule["id"]),
            message=rule["message"],
            triggered_symptoms=symptoms,
        )
