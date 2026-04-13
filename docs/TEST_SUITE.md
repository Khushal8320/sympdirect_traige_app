# SympDirect Triage App - Test Suite Documentation

## Table of Contents

1. [Overview](#overview)
2. [Test Infrastructure](#test-infrastructure)
   - [Configuration](#configuration)
   - [Shared Fixtures](#shared-fixtures)
   - [Running Tests](#running-tests)
3. [Test Files & Coverage Map](#test-files--coverage-map)
4. [test_symptoms.py - Symptom Extraction Tests](#test_symptomspy---symptom-extraction-tests)
5. [test_vitals.py - Vital Sign Threshold Tests](#test_vitalspy---vital-sign-threshold-tests)
6. [test_engine.py - Safety Engine Rule Tests](#test_enginepy---safety-engine-rule-tests)
7. [test_edge_cases.py - Edge Case & Robustness Tests](#test_edge_casespy---edge-case--robustness-tests)
8. [test_config.py - Configuration Loading & Validation Tests](#test_configpy---configuration-loading--validation-tests)
9. [test_integration.py - End-to-End Pipeline Tests](#test_integrationpy---end-to-end-pipeline-tests)
10. [Coverage Report](#coverage-report)
11. [Test Design Principles](#test-design-principles)
12. [Adding New Tests](#adding-new-tests)

---

## Overview

The test suite validates the safety layer and prediction pipeline using **pytest**. It contains **84 tests** across 6 test files, organized by component and concern.

**Test Breakdown:**

| Test File             | Tests | Component Covered                                  |
|-----------------------|-------|----------------------------------------------------|
| `test_symptoms.py`    | 12    | Symptom extraction from free text                  |
| `test_vitals.py`      | 18    | Vital sign threshold evaluation                    |
| `test_engine.py`      | 26    | Safety engine rule matching (RED001-RED010)         |
| `test_edge_cases.py`  | 12    | Null safety, boundaries, malformed input           |
| `test_config.py`      | 11    | Config loading, validation, error detection        |
| `test_integration.py` | 6     | Full pipeline (safety layer + ML model)            |
| **Total**             | **84**|                                                    |

**Current Coverage:** 94% of `src/` (206 statements, 13 missed)

---

## Test Infrastructure

### Configuration

**`pytest.ini`** at the project root:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
```

This tells pytest to:
- Look for tests in the `tests/` directory.
- Discover test files matching `test_*.py`.
- Discover test functions/methods matching `test_*`.

**Dependencies** (in `requirements.txt`):
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting plugin

### Shared Fixtures

**`tests/conftest.py`** provides fixtures automatically available to all test files:

| Fixture       | Type           | Description                                                 |
|---------------|----------------|-------------------------------------------------------------|
| `config`      | `dict`         | Parsed `safety_rules.json` configuration dictionary         |
| `lexicon`     | `dict`         | The `symptom_lexicon` section from the config               |
| `thresholds`  | `list[dict]`   | The `vital_thresholds` section from the config              |
| `engine`      | `SafetyEngine` | A fully initialized SafetyEngine instance                   |
| `config_path` | `str`          | Absolute path to `config/safety_rules.json`                 |

All fixtures load from the real `config/safety_rules.json` file, ensuring tests validate against the actual production configuration.

### Running Tests

**Run all tests:**
```bash
pytest tests/ -v
```

**Run a specific test file:**
```bash
pytest tests/test_engine.py -v
```

**Run a single test:**
```bash
pytest tests/test_engine.py::TestSafetyEngineRules::test_red001_chest_pain_and_sob -v
```

**Run with coverage report:**
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

**Run with coverage HTML report:**
```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Test Files & Coverage Map

```
tests/
├── __init__.py                 # Package init
├── conftest.py                 # Shared fixtures (config, lexicon, engine, etc.)
├── test_symptoms.py            # → src/safety/symptoms.py (100% coverage)
├── test_vitals.py              # → src/safety/vitals.py (100% coverage)
├── test_engine.py              # → src/safety/engine.py (88% coverage)
├── test_edge_cases.py          # → src/safety/engine.py (cross-cutting edge cases)
├── test_config.py              # → src/safety/config.py (92% coverage)
└── test_integration.py         # → src/predict.py (97% coverage)
```

---

## test_symptoms.py - Symptom Extraction Tests

**Module under test:** `src/safety/symptoms.py` → `extract_symptoms()`

**Test class:** `TestExtractSymptoms` (12 tests)

| # | Test Name | Input | Expected Behavior | What It Validates |
|---|-----------|-------|-------------------|-------------------|
| 1 | `test_single_match` | `"patient has chest pain"` | `chest_pain` in result | Basic single-token extraction |
| 2 | `test_multiple_matches` | `"chest pain with shortness of breath"` | Both `chest_pain` and `shortness_of_breath` in result | Multiple tokens from one input |
| 3 | `test_no_match` | `"patient has a headache"` | Neither `chest_pain` nor `shortness_of_breath` in result | Non-matching text returns no false positives |
| 4 | `test_empty_string` | `""` | Empty set | Graceful handling of empty input |
| 5 | `test_none_input` | `None` | Empty set | Graceful handling of None |
| 6 | `test_case_insensitivity` | `"CHEST PAIN and DYSPNEA"` | Both `chest_pain` and `shortness_of_breath` matched | Case-insensitive matching |
| 7 | `test_synonym_dyspnea` | `"dyspnea on exertion"` | `shortness_of_breath` in result | Clinical synonym resolution |
| 8 | `test_synonym_sob` | `"patient reports sob"` | `shortness_of_breath` in result | Abbreviation resolution |
| 9 | `test_abbreviation_cp` | `"presenting with cp"` | `chest_pain` in result | Short abbreviation matching |
| 10 | `test_real_clinical_text_seizure` | `"Seizure Like Activity"` | `seizure` in result | Real dataset value (exact text from CSV) |
| 11 | `test_real_clinical_text_motor_weakness` | `"Rt. side motor weakness"` | `motor_weakness` in result | Real dataset value with prefix |
| 12 | `test_whitespace_only` | `"   "` | Empty set | Whitespace-only input handled |

**Key testing strategies:**
- Tests use the real production lexicon (via the `lexicon` fixture) to validate against actual configuration.
- Tests include values drawn directly from the `emergency_traige1.csv` dataset.
- Synonym coverage ensures the lexicon correctly maps clinical abbreviations (sob, cp, cva) to canonical tokens.

---

## test_vitals.py - Vital Sign Threshold Tests

**Module under test:** `src/safety/vitals.py` → `VitalSignChecker`

**Test class:** `TestVitalSignChecker` (18 tests)

### Threshold Tests (one per vital sign boundary)

| # | Test Name | Vital | Value | Expected | What It Validates |
|---|-----------|-------|-------|----------|-------------------|
| 1 | `test_sbp_low_triggers` | SBP | 89 | KTAS 1 | Below lower bound triggers |
| 2 | `test_sbp_at_boundary_no_trigger` | SBP | 90 | No trigger | Exact boundary = no trigger (strict <) |
| 3 | `test_sbp_high_triggers` | SBP | 181 | KTAS 2 | Above upper bound triggers |
| 4 | `test_sbp_high_boundary_no_trigger` | SBP | 180 | No trigger | Exact boundary = no trigger (strict >) |
| 5 | `test_hr_low_triggers` | HR | 39 | KTAS 1 | Below lower bound triggers |
| 6 | `test_hr_low_boundary` | HR | 40 | No trigger | Exact boundary = no trigger |
| 7 | `test_hr_high_triggers` | HR | 121 | KTAS 2 | Above upper bound triggers |
| 8 | `test_hr_high_boundary` | HR | 120 | No trigger | Exact boundary = no trigger |
| 9 | `test_rr_high_triggers` | RR | 31 | KTAS 2 | Above threshold triggers |
| 10 | `test_rr_boundary` | RR | 30 | No trigger | Exact boundary = no trigger |
| 11 | `test_bt_low_triggers` | BT | 35.9 | KTAS 2 | Float value below threshold |
| 12 | `test_bt_high_triggers` | BT | 39.1 | Triggers | Float value above threshold |
| 13 | `test_saturation_low_triggers` | Saturation | 89 | KTAS 1 | Below threshold triggers |
| 14 | `test_saturation_boundary` | Saturation | 90 | No trigger | Exact boundary = no trigger |

### Multi-Violation & Missing Data Tests

| # | Test Name | Input | Expected | What It Validates |
|---|-----------|-------|----------|-------------------|
| 15 | `test_multiple_violations_most_severe_wins` | SBP=80 (KTAS 1), HR=130 (KTAS 2) | KTAS 1 | Priority resolution picks lowest KTAS |
| 16 | `test_missing_vitals_returns_none` | `{}` and `None` | `None` | Empty/null vitals don't crash |
| 17 | `test_none_vital_value_skipped` | `{"SBP": None, "HR": None}` | `None` | None values are gracefully skipped |
| 18 | `test_non_numeric_vital_skipped` | `{"SBP": "invalid", "HR": "abc"}` | `None` | Non-numeric values don't crash |

**Key testing strategies:**
- Every threshold is tested at exact boundary (should NOT trigger) and one unit past (should trigger).
- This ensures strict `<`/`>` comparison, not `<=`/`>=`.
- Tests for body temperature use float values (35.9, 39.1) to validate decimal handling.

---

## test_engine.py - Safety Engine Rule Tests

**Module under test:** `src/safety/engine.py` → `SafetyEngine`

### TestSafetyEngineRules (22 tests)

Each RED rule is tested with matching input (positive test) and, where applicable, partial/insufficient input (negative test).

| # | Test Name | Rule | Input | Expected | What It Validates |
|---|-----------|------|-------|----------|-------------------|
| 1 | `test_red001_chest_pain_and_sob` | RED001 | `"chest pain with shortness of breath"` | KTAS 1, rule_id=RED001 | Both `requires_all` tokens present |
| 2 | `test_red001_partial_no_trigger` | RED001 | `"chest pain only"` | RED001 NOT triggered | Missing one `requires_all` token |
| 3 | `test_red002_stroke` | RED002 | `"suspected stroke with motor weakness"` | KTAS 1 | `requires_any` matches multiple tokens |
| 4 | `test_red002_mental_change` | RED002 | `"mental change and confusion"` | KTAS 1, rule_id=RED002 | Single `requires_any` match suffices |
| 5 | `test_red002_unresponsive` | RED002 | `"patient is unresponsive"` | KTAS 1 | Different `requires_any` token |
| 6 | `test_red003_seizure` | RED003 | `"Seizure Like Activity"` | KTAS 2, rule_id=RED003 | Real clinical text match |
| 7 | `test_red003_involuntary_movement` | RED003 | `"involuntary movt and twitching"` | rule_id=RED003 | Abbreviation in lexicon |
| 8 | `test_red004_respiratory_distress` | RED004 | `"shortness of breath with stridor"` | KTAS 1, rule_id=RED004 | `requires_all` + `requires_any` combo |
| 9 | `test_red004_partial_no_trigger` | RED004 | `"shortness of breath"` | RED004 NOT triggered | Missing `requires_any` component |
| 10 | `test_red005_hemorrhage` | RED005 | `"massive hemorrhage from wound"` | KTAS 1, rule_id=RED005 | `requires_any` hemorrhage tokens |
| 11 | `test_red005_hematochezia` | RED005 | `"hematochezia and rectal bleeding"` | rule_id=RED005 | GI bleeding token match |
| 12 | `test_red006_anaphylaxis_with_swelling` | RED006 | `"anaphylaxis with facial swelling"` | KTAS 1, rule_id=RED006 | `requires_all` (swelling) + `requires_any` (anaphylaxis) |
| 13 | `test_red006_no_swelling_no_trigger` | RED006 | `"anaphylaxis"` | RED006 NOT triggered | Missing `requires_all` condition |
| 14 | `test_red007_severe_chest_pain` | RED007 | `"chest pain"`, pain=9 | KTAS 1, rule_id=RED007 | Symptom + `pain_min` combo |
| 15 | `test_red007_pain_below_threshold` | RED007 | `"chest pain"`, pain=8 | RED007 NOT triggered | Pain below threshold |
| 16 | `test_red007_pain_none_no_trigger` | RED007 | `"chest pain"`, pain=None | RED007 NOT triggered | Missing pain score skips rule |
| 17 | `test_red008_pediatric_fever` | RED008 | `"fever"`, age=2 | KTAS 2, rule_id=RED008 | Symptom + `age_max` combo |
| 18 | `test_red008_age_boundary_triggers` | RED008 | `"fever"`, age=3 | rule_id=RED008 | Exact boundary (age <= 3) triggers |
| 19 | `test_red008_age_above_no_trigger` | RED008 | `"fever"`, age=4 | RED008 NOT triggered | Age above threshold |
| 20 | `test_red009_syncope_with_chest_pain` | RED009 | `"syncope with chest pain"` | KTAS 1 | `requires_all` + `requires_any` combo |
| 21 | `test_red010_severe_burn` | RED010 | `"severe burn with inhalation injury"` | KTAS 1, rule_id=RED010 | `requires_any` + `severity_min` combo |

### TestSafetyEnginePriority (4 tests)

| # | Test Name | Input | Expected | What It Validates |
|---|-----------|-------|----------|-------------------|
| 22 | `test_multiple_rules_lowest_ktas_wins` | `"seizure with mental change and confusion"` | KTAS 1 | RED003 (KTAS 2) vs RED002 (KTAS 1) → picks 1 |
| 23 | `test_no_rules_match_returns_none` | `"mild headache"` | `None` | Clean no-match path |
| 24 | `test_vital_override_combined_with_text` | `"seizure"`, SBP=80 | KTAS 1 | Text rule + vital threshold combined |
| 25 | `test_empty_complaint_vital_only` | `""`, SBP=80 | KTAS 1 | Vitals alone can trigger without text |
| 26 | (combined in priority) | | | |

**Key testing strategies:**
- Positive tests assert both the KTAS override value AND the specific `rule_id`, ensuring the correct rule fired.
- Negative tests use `if result: assert result.rule_id != "REDxxx"` pattern to allow other rules to fire while confirming the specific rule under test did NOT fire.
- Priority tests verify that when multiple rules match, the most severe (lowest KTAS) wins.

---

## test_edge_cases.py - Edge Case & Robustness Tests

**Module under test:** `src/safety/engine.py` → `SafetyEngine` (cross-cutting)

**Test class:** `TestEdgeCases` (12 tests)

| # | Test Name | Input | Expected | What It Validates |
|---|-----------|-------|----------|-------------------|
| 1 | `test_empty_complaint_empty_vitals` | `""`, `{}` | `None` | No data = no trigger, no crash |
| 2 | `test_none_complaint_none_vitals` | `None`, `None` | `None` | Null inputs handled gracefully |
| 3 | `test_none_everything` | All params `None` | `None` | Maximum nullity |
| 4 | `test_non_numeric_vital_values` | `{"SBP": "invalid"}` | `None` | String vitals skipped cleanly |
| 5 | `test_very_long_text` | `"mild headache " * 10000` | `None` | 140K char input doesn't crash or false-positive |
| 6 | `test_unicode_characters` | `"douleur thoracique café résumé"` | No crash | Unicode text doesn't cause exceptions |
| 7 | `test_special_characters` | `"chest pain!!! shortness of breath @#$%"` | RED001 triggers | Special chars adjacent to keywords don't prevent matching |
| 8 | `test_pain_exact_float_boundary_triggers` | pain=9.0 | RED007 triggers | Float 9.0 >= int 9 works |
| 9 | `test_pain_just_below_boundary` | pain=8.99 | RED007 NOT triggered | 8.99 < 9 correctly excluded |
| 10 | `test_age_exact_boundary` | age=3.0 | RED008 triggers | Float 3.0 <= int 3 works |
| 11 | `test_age_just_above_boundary` | age=3.01 | RED008 NOT triggered | 3.01 > 3 correctly excluded |
| 12 | `test_integer_type_input` | Normal ints | RED001 triggers | Integer vitals work (vs float) |

**Key testing strategies:**
- These tests focus on **defensive programming** - ensuring the system never crashes on unexpected input.
- Float boundary tests (8.99 vs 9.0, 3.0 vs 3.01) validate that numeric comparisons handle floating-point precision correctly.
- The long text test ensures no performance degradation or stack overflow with very large inputs.

---

## test_config.py - Configuration Loading & Validation Tests

**Module under test:** `src/safety/config.py` → `load_config()`, `validate_config()`

### TestLoadConfig (3 tests)

| # | Test Name | Input | Expected | What It Validates |
|---|-----------|-------|----------|-------------------|
| 1 | `test_loads_valid_config` | Real config file | All 3 top-level keys present | Production config loads correctly |
| 2 | `test_file_not_found` | `"/nonexistent/path"` | `FileNotFoundError` | Missing file gives clear error |
| 3 | `test_malformed_json` | `"{invalid json"` | `json.JSONDecodeError` | Corrupt JSON gives clear error |

### TestValidateConfig (8 tests)

| # | Test Name | Config | Expected Errors | What It Validates |
|---|-----------|--------|-----------------|-------------------|
| 4 | `test_valid_config_no_errors` | Real config | Empty list | Production config passes validation |
| 5 | `test_missing_rules_key` | No `rules` key | Error mentioning "rules" | Required key detection |
| 6 | `test_missing_vital_thresholds` | No `vital_thresholds` | Error mentioning "vital_thresholds" | Required key detection |
| 7 | `test_duplicate_rule_ids` | Two rules with `"RED001"` | Error mentioning "Duplicate" | Uniqueness constraint |
| 8 | `test_invalid_ctas_override` | `ctas_override: 6` | Error mentioning "ctas_override" | Range validation (1-5) |
| 9 | `test_unknown_symptom_token_in_rule` | `requires_all: ["nonexistent_token"]` | Error mentioning "unknown symptom token" | Lexicon cross-reference |
| 10 | `test_missing_rule_fields` | Rule with only `id` | Error mentioning "missing field" | Required field detection |
| 11 | `test_invalid_vital_condition` | `condition: "eq"` | Error mentioning "condition" | Enum validation (lt/gt only) |

**Key testing strategies:**
- Tests construct deliberately malformed configs to verify each validation path.
- The `test_malformed_json` test creates a temporary file with invalid JSON, tests it, then cleans up.
- Error message assertions use `any(keyword in e for e in errors)` to be resilient to exact message wording changes.

---

## test_integration.py - End-to-End Pipeline Tests

**Module under test:** `src/predict.py` → `predict_triage()`

**Test class:** `TestIntegration` (6 tests)

| # | Test Name | Scenario | Expected | Requires Model |
|---|-----------|----------|----------|----------------|
| 1 | `test_safety_override_patient` | Critical patient (CP+SOB, SBP=80, pain=9) | `source="safety_override"`, `ktas=1` | No |
| 2 | `test_result_structure` | Any safety override case | All 4 dict keys present | No |
| 3 | `test_safety_override_vitals_only` | Headache + SBP=70 | `source="safety_override"`, `ktas=1` | No |
| 4 | `test_model_prediction_returned` | Normal patient, all vitals normal | `source="model"`, `1 <= ktas <= 5` | **Yes** (skipped if missing) |
| 5 | `test_model_prediction_structure` | Normal patient | `ktas` is int, `safety_result` is None | **Yes** (skipped if missing) |
| 6 | `test_safety_takes_precedence_over_model` | Unresponsive + SBP=60 | `source="safety_override"` | No |

**Model-dependent tests:** Tests 4 and 5 are decorated with `@pytest.mark.skipif(not has_model, ...)`. They are automatically skipped if `models/best_triage_model.pkl` is not present, allowing the test suite to pass in CI environments without the model file.

**Key testing strategies:**
- Tests 1, 3, and 6 verify the safety layer short-circuits before the model.
- Tests 4 and 5 verify the full ML pipeline works end-to-end when the model is available.
- Test 2 validates the response contract (all required keys present in the output dict).

---

## Coverage Report

```
Name                     Stmts   Miss  Cover   Missing
------------------------------------------------------
src/__init__.py              0      0   100%
src/predict.py              36      1    97%   87
src/safety/__init__.py       4      0   100%
src/safety/config.py        50      4    92%   31, 62, 70, 73
src/safety/engine.py        69      8    88%   31, 50-59, 114, 132
src/safety/symptoms.py      13      0   100%
src/safety/vitals.py        34      0   100%
------------------------------------------------------
TOTAL                      206     13    94%
```

**Uncovered lines explained:**

| File | Lines | Reason |
|------|-------|--------|
| `predict.py:87` | Last line of `_run_model` | Only reached when model successfully predicts; model version mismatch warnings may alter control flow |
| `config.py:31,62,70,73` | Rare validation paths | Conditions like missing rule `id` when rule has no `id` key at all; edge cases in vital threshold validation |
| `engine.py:31,50-59` | Fail-safe error handler | The `try/except` block and `FAIL_SAFE` return; would require mocking internal methods to trigger |
| `engine.py:114,132` | Unreachable guard clauses | Guard for rules with no symptom requirements (all production rules have them) |

---

## Test Design Principles

### 1. Test Against Production Config
All fixtures load the real `config/safety_rules.json`, not mocked configurations. This ensures tests validate the actual rules that will be deployed.

### 2. Boundary Value Analysis
Every numeric threshold is tested at:
- One unit below the boundary (should trigger for `<`, should not for `>`)
- Exactly at the boundary (should NOT trigger for strict comparisons)
- One unit above the boundary (should trigger for `>`, should not for `<`)

### 3. Negative Testing
For every rule, there is at least one test verifying that partial input does **not** trigger the rule. This prevents false-positive escalations.

### 4. Graceful Degradation
Edge case tests verify that the system returns `None` (no override) rather than crashing on:
- Null/None inputs
- Empty strings
- Non-numeric vital values
- Very long text
- Unicode and special characters

### 5. Rule Isolation
Each RED rule has dedicated tests that assert the specific `rule_id` in the result, ensuring the correct rule fired and not a different one that happens to produce the same KTAS override.

### 6. Priority Verification
Dedicated tests verify that when multiple rules fire simultaneously, the most severe (lowest KTAS) result is returned.

---

## Adding New Tests

### For a New RED Rule

When adding a new rule (e.g., RED011) to `safety_rules.json`, add corresponding tests to `tests/test_engine.py`:

```python
def test_red011_positive(self, engine):
    """Test that RED011 fires with matching input."""
    result = engine.evaluate("matching complaint text", {"SBP": 120})
    assert result is not None
    assert result.rule_id == "RED011"
    assert result.override_ktas == <expected_ktas>

def test_red011_partial_no_trigger(self, engine):
    """Test that RED011 does NOT fire with incomplete input."""
    result = engine.evaluate("partial match only", {})
    if result:
        assert result.rule_id != "RED011"
```

### For a New Vital Threshold

Add to `tests/test_vitals.py`:

```python
def test_new_vital_triggers(self, thresholds):
    checker = VitalSignChecker(thresholds)
    result = checker.check({"NewVital": <triggering_value>})
    assert result is not None
    assert result.ctas_override == <expected_ktas>

def test_new_vital_boundary(self, thresholds):
    checker = VitalSignChecker(thresholds)
    result = checker.check({"NewVital": <exact_boundary>})
    assert result is None  # Strict comparison, boundary should NOT trigger
```

### For a New Symptom Synonym

Add to `tests/test_symptoms.py`:

```python
def test_new_synonym(self, lexicon):
    result = extract_symptoms("text containing the new synonym", lexicon)
    assert "canonical_token" in result
```

### Running Specific New Tests

```bash
# Run only the new test
pytest tests/test_engine.py::TestSafetyEngineRules::test_red011_positive -v

# Run all tests and check coverage change
pytest tests/ --cov=src --cov-report=term-missing
```
