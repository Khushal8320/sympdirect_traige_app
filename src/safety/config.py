import json
from pathlib import Path


def load_config(path: str) -> dict:
    """Load and parse the safety rules JSON configuration."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(config_path, "r") as f:
        return json.load(f)


def validate_config(config: dict) -> list[str]:
    """Validate the safety rules configuration. Returns list of error strings."""
    errors = []

    # Check top-level keys
    for key in ("rules", "vital_thresholds", "symptom_lexicon"):
        if key not in config:
            errors.append(f"Missing required top-level key: '{key}'")

    if "rules" not in config:
        return errors

    # Check rule IDs are unique
    rule_ids = [r.get("id") for r in config["rules"]]
    seen = set()
    for rid in rule_ids:
        if rid is None:
            errors.append("Rule missing required field: 'id'")
        elif rid in seen:
            errors.append(f"Duplicate rule ID: '{rid}'")
        seen.add(rid)

    lexicon_tokens = set(config.get("symptom_lexicon", {}).keys())

    for rule in config["rules"]:
        # Required fields
        for field in ("id", "pattern", "ctas_override", "message"):
            if field not in rule:
                errors.append(f"Rule '{rule.get('id', '?')}' missing field: '{field}'")

        # CTAS override must be 1-5
        ctas = rule.get("ctas_override")
        if ctas is not None and (not isinstance(ctas, int) or ctas < 1 or ctas > 5):
            errors.append(
                f"Rule '{rule.get('id', '?')}' has invalid ctas_override: {ctas} (must be 1-5)"
            )

        # Symptom tokens in pattern must exist in lexicon
        pattern = rule.get("pattern", {})
        for key in ("requires_all", "requires_any"):
            for token in pattern.get(key, []):
                if token not in lexicon_tokens:
                    errors.append(
                        f"Rule '{rule.get('id', '?')}' references unknown symptom token: '{token}'"
                    )

        severity = pattern.get("severity_min")
        if severity and severity not in lexicon_tokens:
            errors.append(
                f"Rule '{rule.get('id', '?')}' references unknown severity token: '{severity}'"
            )

    # Validate vital thresholds
    for threshold in config.get("vital_thresholds", []):
        for field in ("vital", "condition", "value", "ctas_override", "reason"):
            if field not in threshold:
                errors.append(f"Vital threshold missing field: '{field}'")
        ctas = threshold.get("ctas_override")
        if ctas is not None and (not isinstance(ctas, int) or ctas < 1 or ctas > 5):
            errors.append(
                f"Vital threshold has invalid ctas_override: {ctas} (must be 1-5)"
            )
        condition = threshold.get("condition")
        if condition and condition not in ("lt", "gt"):
            errors.append(
                f"Vital threshold has invalid condition: '{condition}' (must be 'lt' or 'gt')"
            )

    return errors
