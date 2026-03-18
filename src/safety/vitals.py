from dataclasses import dataclass


@dataclass
class VitalViolation:
    """A single vital sign threshold violation."""
    vital: str
    ctas_override: int
    reason: str


class VitalSignChecker:
    """Checks vital signs against configured thresholds."""

    def __init__(self, thresholds: list[dict]):
        self.thresholds = thresholds

    def check(self, vitals: dict) -> VitalViolation | None:
        """Evaluate vitals against thresholds.

        Returns the most severe violation (lowest KTAS override), or None.
        """
        if not vitals:
            return None

        worst = None

        for threshold in self.thresholds:
            vital_name = threshold["vital"]
            value = vitals.get(vital_name)

            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            condition = threshold["condition"]
            limit = threshold["value"]
            triggered = False

            if condition == "lt" and value < limit:
                triggered = True
            elif condition == "gt" and value > limit:
                triggered = True

            if triggered:
                violation = VitalViolation(
                    vital=vital_name,
                    ctas_override=threshold["ctas_override"],
                    reason=threshold["reason"],
                )
                if worst is None or violation.ctas_override < worst.ctas_override:
                    worst = violation

        return worst
