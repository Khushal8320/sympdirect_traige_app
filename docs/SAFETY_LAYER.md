# SympDirect Triage App - Safety Layer Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration: safety_rules.json](#configuration-safety_rulesjson)
   - [Rules Section](#rules-section)
   - [Vital Thresholds Section](#vital-thresholds-section)
   - [Symptom Lexicon Section](#symptom-lexicon-section)
   - [Fail Mode](#fail-mode)
4. [Module Reference](#module-reference)
   - [config.py - Configuration Loader & Validator](#configpy---configuration-loader--validator)
   - [symptoms.py - Symptom Extraction](#symptomspy---symptom-extraction)
   - [vitals.py - Vital Sign Checker](#vitalspy---vital-sign-checker)
   - [engine.py - Safety Engine (Orchestrator)](#enginepy---safety-engine-orchestrator)
   - [predict.py - Prediction Pipeline](#predictpy---prediction-pipeline)
5. [Clinical Red-Flag Rules (RED001-RED010)](#clinical-red-flag-rules-red001-red010)
6. [Evaluation Flow](#evaluation-flow)
7. [Data Structures](#data-structures)
8. [Usage Examples](#usage-examples)
9. [Adding New Rules](#adding-new-rules)
10. [Design Decisions & Rationale](#design-decisions--rationale)

---

## Overview

The Safety Layer is a deterministic, rule-based clinical safeguard that sits **in front of** the ML triage prediction model (XGBoost + SMOTE). Its purpose is to catch life-threatening clinical patterns and auto-escalate them to CTAS/KTAS 1 or 2 **before** the probabilistic ML model is consulted.

**Key Principles:**

- **Deterministic**: No randomness or probability. The same input always produces the same output.
- **Fail-safe**: On unexpected errors, the engine escalates to KTAS 1 rather than silently failing.
- **Configurable**: All rules, thresholds, and symptom synonyms live in a JSON file, not in code.
- **Non-blocking**: If no red flags are detected, the request passes through to the ML model unchanged.

**Why a Safety Layer?**

ML models can misclassify rare but critical presentations. A patient presenting with "chest pain and shortness of breath" must **never** be assigned KTAS 4 or 5 regardless of what the model predicts. The safety layer provides a hard floor on acuity for known life-threatening patterns.

---

## Architecture

```
Patient Data (chief complaint, vitals, pain score, age)
                    │
                    ▼
          ┌─────────────────┐
          │  predict_triage()│  ← Entry point (src/predict.py)
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  SafetyEngine    │  ← Rule-based evaluator (src/safety/engine.py)
          │  .evaluate()     │
          └────────┬────────┘
                   │
          ┌────────┼────────────────┐
          │        │                │
          ▼        ▼                ▼
   ┌────────┐ ┌──────────┐  ┌──────────────┐
   │Symptom │ │  Rule     │  │VitalSign     │
   │Extract │ │  Matching │  │Checker       │
   │        │ │(10 rules) │  │(8 thresholds)│
   └────────┘ └──────────┘  └──────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     SafetyResult      None (no match)
     (override)             │
          │                 ▼
          │        ┌─────────────────┐
          │        │  ML Model       │
          │        │  (XGBoost+SMOTE)│
          │        └────────┬────────┘
          │                 │
          ▼                 ▼
   ┌────────────────────────────┐
   │  Response Dict             │
   │  {ktas, source, ...}      │
   └────────────────────────────┘
```

**File Structure:**

```
sympdirect_traige_app/
├── config/
│   └── safety_rules.json          # All rules, thresholds, and symptom lexicon
├── src/
│   ├── __init__.py
│   ├── safety/
│   │   ├── __init__.py            # Package exports
│   │   ├── config.py              # load_config(), validate_config()
│   │   ├── symptoms.py            # extract_symptoms()
│   │   ├── vitals.py              # VitalSignChecker class
│   │   └── engine.py              # SafetyEngine class + SafetyResult dataclass
│   └── predict.py                 # predict_triage() - unified pipeline entry point
```

---

## Configuration: safety_rules.json

The configuration file is located at `config/safety_rules.json` and contains three main sections plus a fail mode setting.

### Rules Section

Each rule object in the `"rules"` array has the following schema:

| Field            | Type   | Required | Description                                                       |
|------------------|--------|----------|-------------------------------------------------------------------|
| `id`             | string | Yes      | Unique identifier (e.g., `"RED001"`)                              |
| `name`           | string | Yes      | Human-readable rule name                                          |
| `pattern`        | object | Yes      | Matching conditions (see Pattern Fields below)                    |
| `ctas_override`  | int    | Yes      | KTAS/CTAS score to assign if rule fires (1-5, 1 = most critical) |
| `message`        | string | Yes      | Clinical explanation shown when rule triggers                     |

**Pattern Fields:**

| Field          | Type       | Description                                                                           |
|----------------|------------|---------------------------------------------------------------------------------------|
| `requires_all` | `string[]` | ALL listed symptom tokens must be present in the chief complaint                      |
| `requires_any` | `string[]` | At least ONE listed symptom token must be present                                     |
| `pain_min`     | `number`   | NRS pain score must be >= this value (skipped if pain score is not provided)           |
| `age_max`      | `number`   | Patient age must be <= this value (skipped if age is not provided)                     |
| `severity_min` | `string`   | This symptom token must also be present in extracted symptoms (severity qualifier)     |

**Evaluation Logic:** A rule fires only when ALL specified conditions in its pattern are satisfied simultaneously. Conditions that are not specified in the pattern are not evaluated (they don't block the rule).

### Vital Thresholds Section

Each threshold object in `"vital_thresholds"`:

| Field           | Type   | Required | Description                                          |
|-----------------|--------|----------|------------------------------------------------------|
| `vital`         | string | Yes      | Vital sign key matching the input dict (e.g., `"SBP"`, `"HR"`, `"BT"`, `"Saturation"`) |
| `condition`     | string | Yes      | `"lt"` (less than) or `"gt"` (greater than)          |
| `value`         | number | Yes      | Threshold value (strict comparison, not <=/>= )      |
| `ctas_override` | int    | Yes      | KTAS override if threshold is breached (1-5)         |
| `reason`        | string | Yes      | Clinical explanation                                 |

**Configured Thresholds (8 total):**

| Vital      | Condition | Value | KTAS Override | Clinical Meaning            |
|------------|-----------|-------|---------------|-----------------------------|
| SBP        | < (lt)    | 90    | 1             | Hypotension                 |
| SBP        | > (gt)    | 180   | 2             | Hypertensive crisis         |
| HR         | < (lt)    | 40    | 1             | Severe bradycardia          |
| HR         | > (gt)    | 120   | 2             | Tachycardia                 |
| RR         | > (gt)    | 30    | 2             | Tachypnea                   |
| BT         | < (lt)    | 36    | 2             | Hypothermia                 |
| BT         | > (gt)    | 39    | 2             | High fever                  |
| Saturation | < (lt)    | 90    | 1             | Severe hypoxia              |

**Boundary Behavior:** All comparisons are **strict** (< or >), not <= or >=. For example, SBP = 90 does **not** trigger the hypotension threshold; SBP = 89 does.

### Symptom Lexicon Section

The `"symptom_lexicon"` maps canonical symptom tokens to arrays of natural language phrases that represent them in clinical text.

**Structure:**
```json
{
  "canonical_token": ["phrase 1", "phrase 2", "abbreviation", ...]
}
```

**Purpose:** Bridges the gap between free-text chief complaints (e.g., `"pt c/o sob and cp"`) and the structured symptom tokens referenced by rules (e.g., `shortness_of_breath`, `chest_pain`).

**Current Lexicon (27 tokens):**

| Token                      | Example Phrases                                              |
|----------------------------|--------------------------------------------------------------|
| `chest_pain`               | chest pain, chest tightness, crushing chest, cp              |
| `shortness_of_breath`      | shortness of breath, dyspnea, sob, breathlessness            |
| `syncope`                  | syncope, fainting, loss of consciousness, passed out         |
| `seizure`                  | seizure, seizure like activity, convulsion, fitting           |
| `involuntary_movement`     | involuntary movement, involuntary movt, tremor               |
| `unresponsive`             | unresponsive, not responding, no response                    |
| `unconscious`              | unconscious, comatose, coma                                  |
| `stroke`                   | stroke, cva, cerebrovascular                                 |
| `motor_weakness`           | motor weakness, hemiparesis, hemiplegia                      |
| `mental_change`            | mental change, altered mental status, confusion, confused     |
| `fever`                    | fever, febrile, high temperature, pyrexia                    |
| `high_temperature`         | high temperature, hyperthermia, fever                        |
| `palpitation`              | palpitation, palpitations, heart racing                      |
| `hemorrhage`               | hemorrhage, massive bleeding, exsanguination                 |
| `hematemesis`              | hematemesis, vomiting blood, blood vomit                     |
| `hematochezia`             | hematochezia, bloody stool, rectal bleeding                  |
| `major_bleeding`           | major bleeding, severe bleeding, active bleeding             |
| `epigastric_pain`          | epigastric pain, upper abdominal pain                        |
| `burn`                     | burn, thermal burn, chemical burn, scald                     |
| `severe_burn`              | severe burn, third degree burn, major burn                   |
| `inhalation_injury`        | inhalation injury, smoke inhalation, airway burn             |
| `anaphylaxis`              | anaphylaxis, anaphylactic shock                              |
| `allergic_reaction_severe` | severe allergic reaction, allergic emergency                 |
| `swelling`                 | swelling, angioedema, edema, swollen                         |
| `cyanosis`                 | cyanosis, cyanotic, blue lips, blue skin                     |
| `choking`                  | choking, airway obstruction, foreign body airway             |
| `stridor`                  | stridor, inspiratory stridor, upper airway noise             |

Phrases were drawn from real `Chief_complain_clean` values in the `emergency_traige1.csv` dataset.

### Fail Mode

```json
"fail_mode": "escalate"
```

When set to `"escalate"`, any unexpected exception during safety evaluation results in a KTAS 1 override with rule ID `"FAIL_SAFE"`. This ensures that a coding error or data issue never silently downgrades a potentially critical patient.

---

## Module Reference

### config.py - Configuration Loader & Validator

**Location:** `src/safety/config.py`

#### `load_config(path: str) -> dict`

Reads and parses a JSON file from the given path.

- **Parameters:** `path` - Absolute or relative path to the JSON configuration file.
- **Returns:** Parsed dictionary.
- **Raises:** `FileNotFoundError` if the file does not exist; `json.JSONDecodeError` if the file contains invalid JSON.

#### `validate_config(config: dict) -> list[str]`

Validates the structure and integrity of a safety rules configuration dictionary.

- **Parameters:** `config` - The parsed configuration dictionary.
- **Returns:** A list of human-readable error strings. An empty list means the configuration is valid.

**Validations performed:**
1. Required top-level keys exist: `rules`, `vital_thresholds`, `symptom_lexicon`.
2. All rule IDs are non-null and unique.
3. Each rule has required fields: `id`, `pattern`, `ctas_override`, `message`.
4. All `ctas_override` values are integers in range 1-5.
5. All symptom tokens referenced in rule patterns (`requires_all`, `requires_any`, `severity_min`) exist as keys in the symptom lexicon.
6. Vital threshold entries have all required fields and valid conditions (`"lt"` or `"gt"`).

---

### symptoms.py - Symptom Extraction

**Location:** `src/safety/symptoms.py`

#### `extract_symptoms(text: str | None, lexicon: dict) -> set[str]`

Converts a free-text chief complaint string into a set of canonical symptom tokens using the configured lexicon.

- **Parameters:**
  - `text` - Raw chief complaint string (may be `None` or empty).
  - `lexicon` - Dictionary mapping canonical tokens to lists of synonym phrases.
- **Returns:** A set of matched canonical token strings (e.g., `{"chest_pain", "shortness_of_breath"}`).

**Algorithm:**
1. If `text` is `None`, empty, or not a string, return empty set.
2. Lowercase and strip the input.
3. For each token in the lexicon, check if any of its phrases appear as a **substring** in the lowered text.
4. On first phrase match for a token, add the token to the result and move to the next token.

**Design notes:**
- Substring matching means `"chest pain"` matches inside `"severe chest pain radiating to arm"`.
- Case insensitive: `"CHEST PAIN"` matches `"chest pain"`.
- Special characters adjacent to keywords do not prevent matching (e.g., `"chest pain!!!"` still matches `"chest pain"`).

---

### vitals.py - Vital Sign Checker

**Location:** `src/safety/vitals.py`

#### Class: `VitalViolation` (dataclass)

| Field           | Type  | Description                       |
|-----------------|-------|-----------------------------------|
| `vital`         | `str` | Vital sign name (e.g., `"SBP"`)  |
| `ctas_override` | `int` | KTAS override value (1-5)        |
| `reason`        | `str` | Clinical explanation              |

#### Class: `VitalSignChecker`

**Constructor:** `__init__(self, thresholds: list[dict])`
- Takes the `vital_thresholds` list from the configuration.

**Method:** `check(self, vitals: dict) -> VitalViolation | None`

Evaluates a patient's vital signs against all configured thresholds.

- **Parameters:** `vitals` - Dictionary of vital sign measurements (e.g., `{"SBP": 85, "HR": 130}`).
- **Returns:** The most severe `VitalViolation` (lowest KTAS override), or `None` if no thresholds are breached.

**Behavior with missing/invalid data:**
- `None` dict or empty dict: returns `None` (no crash).
- `None` value for a specific vital: skipped.
- Non-numeric value (e.g., `"invalid"`): skipped (caught by `float()` conversion).

**Priority resolution:** When multiple vital thresholds are breached simultaneously, the violation with the **lowest** `ctas_override` (most severe) is returned.

---

### engine.py - Safety Engine (Orchestrator)

**Location:** `src/safety/engine.py`

#### Class: `SafetyResult` (dataclass)

The return value when a safety rule or vital threshold fires.

| Field                | Type       | Description                                                  |
|----------------------|------------|--------------------------------------------------------------|
| `override_ktas`      | `int`      | KTAS score to assign (1 = most critical, 5 = least)         |
| `rule_id`            | `str`      | ID of the triggered rule (e.g., `"RED001"`, `"VITAL_SBP"`)  |
| `reason`             | `str`      | Rule name or clinical reason                                 |
| `message`            | `str`      | Detailed message for clinical display                        |
| `triggered_symptoms` | `set[str]` | Set of symptom tokens that were extracted (default: empty)   |

#### Class: `SafetyEngine`

**Constructor:** `__init__(self, config_path: str)`

- Loads the configuration via `load_config()`.
- Validates it via `validate_config()`; raises `ValueError` if invalid.
- Initializes the `VitalSignChecker` with configured thresholds.

**Method:** `evaluate(self, chief_complaint, vitals, pain_score=None, age=None) -> SafetyResult | None`

Main evaluation entry point.

- **Parameters:**
  - `chief_complaint` (`str | None`) - Free-text chief complaint.
  - `vitals` (`dict | None`) - Vital sign measurements.
  - `pain_score` (`float | None`) - NRS pain score (0-10).
  - `age` (`float | None`) - Patient age in years.
- **Returns:** Most severe `SafetyResult`, or `None` if nothing fires.

**Evaluation order:**
1. Extract symptoms from chief complaint text via the lexicon.
2. Evaluate all 10 pattern-based rules against extracted symptoms + pain/age.
3. Evaluate all vital sign thresholds.
4. Across all matches (rules + vitals), return the one with the **lowest** `override_ktas`.
5. If nothing matched, return `None`.

**Error handling:** Wraps the internal evaluation in a try/except. On unexpected error with `fail_mode: "escalate"`, returns a `SafetyResult` with `override_ktas=1` and `rule_id="FAIL_SAFE"`.

---

### predict.py - Prediction Pipeline

**Location:** `src/predict.py`

#### `predict_triage(chief_complaint, vitals, pain_score, age, sex, ktas_rn, model_path, config_path) -> dict`

Unified entry point that runs the safety layer first, then falls through to the ML model.

- **Parameters:**
  - `chief_complaint` (`str`) - Free-text chief complaint.
  - `vitals` (`dict`) - Vital sign measurements.
  - `pain_score` (`float | None`) - NRS pain score.
  - `age` (`float | None`) - Patient age.
  - `sex` (`str | None`) - Patient sex.
  - `ktas_rn` (`str | None`) - KTAS registered nurse assessment.
  - `model_path` (`str`) - Path to the model `.pkl` file (defaults to `models/best_triage_model.pkl`).
  - `config_path` (`str`) - Path to the safety rules JSON (defaults to `config/safety_rules.json`).

- **Returns:**

```python
{
    "ktas": int,              # Final KTAS score (1-5)
    "source": str,            # "safety_override" or "model"
    "safety_result": SafetyResult | None,  # Present if safety triggered
    "model_prediction": int | None         # Present if model was used
}
```

**ML Model Integration:**

The model `.pkl` file is a dictionary bundle with keys:
- `model_name` - Identifier string (e.g., `"Model B XGBoost+SMOTE"`)
- `preprocessor` - Fitted `sklearn.compose.ColumnTransformer` (handles TF-IDF on text + scaling on numerics + one-hot on categoricals)
- `classifier` - Fitted `xgboost.XGBClassifier`
- `label_shift` - Integer offset to add to classifier output to get KTAS score (value: `1`)
- `features` - Dictionary describing expected input columns:
  - `text`: `"Chief_complain_clean"`
  - `numerical`: `["SBP", "DBP", "HR", "RR", "BT", "NRS_pain", "Age"]`
  - `categorical`: `["Sex", "KTAS_RN"]`

---

## Clinical Red-Flag Rules (RED001-RED010)

### RED001 - Acute Coronary Syndrome
- **Conditions:** `chest_pain` AND `shortness_of_breath` both present
- **Override:** KTAS 1
- **Rationale:** Co-occurrence of chest pain and dyspnea is the classic ACS presentation and requires immediate assessment.

### RED002 - Stroke Symptoms
- **Conditions:** ANY of: `unresponsive`, `unconscious`, `stroke`, `motor_weakness`, `mental_change`
- **Override:** KTAS 1
- **Rationale:** Any single sign of acute neurological compromise warrants highest priority. Time-critical for thrombolysis window.

### RED003 - Seizure Activity
- **Conditions:** ANY of: `seizure`, `involuntary_movement`
- **Override:** KTAS 2
- **Rationale:** Active or recent seizure activity needs urgent assessment for status epilepticus and underlying cause.

### RED004 - Severe Respiratory Distress
- **Conditions:** `shortness_of_breath` AND ANY of: `cyanosis`, `choking`, `stridor`
- **Override:** KTAS 1
- **Rationale:** Dyspnea with airway compromise signs indicates potential complete obstruction. SOB alone is KTAS 2-3; adding cyanosis/stridor/choking escalates to immediate.

### RED005 - Massive Hemorrhage
- **Conditions:** ANY of: `hemorrhage`, `hematemesis`, `hematochezia`, `major_bleeding`
- **Override:** KTAS 1
- **Rationale:** Active significant bleeding from any source requires immediate hemodynamic stabilization.

### RED006 - Anaphylaxis
- **Conditions:** `swelling` AND ANY of: `anaphylaxis`, `allergic_reaction_severe`
- **Override:** KTAS 1
- **Rationale:** Anaphylaxis with visible swelling suggests airway compromise risk. Requires immediate epinephrine consideration.

### RED007 - Severe Pain with Cardiac Risk
- **Conditions:** ANY of: `chest_pain`, `epigastric_pain` AND `pain_score >= 9`
- **Override:** KTAS 1
- **Rationale:** Very high pain (NRS >= 9) at cardiac risk locations suggests acute MI or aortic dissection. Note: if pain score is not provided, this rule is skipped.

### RED008 - Pediatric Fever Emergency
- **Conditions:** ANY of: `fever`, `high_temperature` AND `age <= 3`
- **Override:** KTAS 2
- **Rationale:** Fever in children aged 3 or younger carries risk of occult bacteremia and meningitis. Note: if age is not provided, this rule is skipped.

### RED009 - Syncope with Cardiac History
- **Conditions:** `syncope` AND ANY of: `chest_pain`, `palpitation`, `shortness_of_breath`
- **Override:** KTAS 1
- **Rationale:** Syncope with concurrent cardiac symptoms suggests arrhythmia or structural heart disease.

### RED010 - Severe Burn
- **Conditions:** ANY of: `burn`, `inhalation_injury` AND `severity_min: severe_burn`
- **Override:** KTAS 1
- **Rationale:** The `severity_min` field requires that the text also contains phrases matching `severe_burn` (e.g., "severe burn", "third degree burn"). Simple burns without severity indicators do not trigger this rule.

---

## Evaluation Flow

**Step-by-step for a single patient evaluation:**

```
1. SafetyEngine.evaluate() is called
   │
2. extract_symptoms(chief_complaint, lexicon)
   │  → e.g., {"chest_pain", "shortness_of_breath"}
   │
3. For each rule (RED001 → RED010):
   │  a. Check requires_all → all tokens in extracted set?
   │  b. Check requires_any → any token in extracted set?
   │  c. If no symptom requirements exist → skip (don't fire on nothing)
   │  d. Check pain_min → pain_score >= threshold? (skip if None)
   │  e. Check age_max → age <= threshold? (skip if None)
   │  f. Check severity_min → token in extracted set?
   │  g. ALL conditions met → candidate SafetyResult
   │
4. VitalSignChecker.check(vitals)
   │  → For each threshold: convert value to float, compare with lt/gt
   │  → Return worst violation (lowest KTAS)
   │
5. Compare all candidates (rule results + vital result)
   │  → Pick the one with the lowest override_ktas
   │
6. Return SafetyResult or None
```

**Priority resolution example:**

If a patient triggers:
- RED003 (seizure) → KTAS 2
- RED002 (mental change) → KTAS 1
- VITAL_HR (HR > 120) → KTAS 2

The engine returns the RED002 result (KTAS 1) because it is the most severe.

---

## Data Structures

### Input: Patient Data

```python
chief_complaint: str    # "chest pain with shortness of breath"
vitals: dict            # {"SBP": 85, "HR": 130, "RR": 22, "BT": 37.0, "Saturation": 94}
pain_score: float       # 9.0 (NRS scale 0-10)
age: float              # 55.0 (years)
```

### Output: Prediction Result

```python
# When safety layer triggers:
{
    "ktas": 1,
    "source": "safety_override",
    "safety_result": SafetyResult(
        override_ktas=1,
        rule_id="RED001",
        reason="Acute Coronary Syndrome",
        message="Possible acute coronary syndrome: chest pain with dyspnea",
        triggered_symptoms={"chest_pain", "shortness_of_breath"}
    ),
    "model_prediction": None
}

# When no safety rules fire (model decides):
{
    "ktas": 3,
    "source": "model",
    "safety_result": None,
    "model_prediction": 3
}
```

---

## Usage Examples

### Direct Safety Engine Usage

```python
from src.safety.engine import SafetyEngine

engine = SafetyEngine("config/safety_rules.json")

# Critical patient - chest pain + SOB
result = engine.evaluate(
    chief_complaint="chest pain with shortness of breath",
    vitals={"SBP": 85, "HR": 130},
    pain_score=9,
    age=55
)
# → SafetyResult(override_ktas=1, rule_id="RED001", ...)

# Non-critical patient - no rules fire
result = engine.evaluate(
    chief_complaint="mild headache",
    vitals={"SBP": 120, "HR": 80}
)
# → None
```

### Full Pipeline Usage

```python
from src.predict import predict_triage

result = predict_triage(
    chief_complaint="patient reports syncope and palpitations",
    vitals={"SBP": 110, "HR": 95, "RR": 18, "BT": 36.8, "Saturation": 97},
    pain_score=5,
    age=68,
    sex="M",
    ktas_rn="3",
)
# result["ktas"] → 1 (safety override from RED009)
# result["source"] → "safety_override"
```

### Symptom Extraction Only

```python
from src.safety.symptoms import extract_symptoms
from src.safety.config import load_config

config = load_config("config/safety_rules.json")
lexicon = config["symptom_lexicon"]

symptoms = extract_symptoms("Rt. side motor weakness with confusion", lexicon)
# → {"motor_weakness", "mental_change"}
```

---

## Adding New Rules

To add a new safety rule:

1. **Add synonym phrases** to `"symptom_lexicon"` in `config/safety_rules.json` for any new symptom tokens your rule needs.

2. **Add the rule** to the `"rules"` array:

```json
{
    "id": "RED011",
    "name": "Your Rule Name",
    "pattern": {
        "requires_all": ["token_a"],
        "requires_any": ["token_b", "token_c"],
        "pain_min": 7,
        "age_max": 65
    },
    "ctas_override": 2,
    "message": "Clinical explanation for this override"
}
```

3. **Run validation:**
```python
from src.safety.config import load_config, validate_config
config = load_config("config/safety_rules.json")
errors = validate_config(config)
assert errors == [], errors
```

4. **Add corresponding tests** to `tests/test_engine.py`.

---

## Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| **JSON config over hardcoded rules** | Clinical rules evolve. Clinicians can review and modify JSON without touching Python code. |
| **Substring matching for symptoms** | Clinical text is messy. Substring matching handles embedded phrases like "severe chest pain radiating to arm" without requiring tokenization. |
| **Strict comparisons (< / >) for vitals** | Avoids ambiguity at exact boundary values. A SBP of exactly 90 is borderline, not definitively hypotensive. |
| **Most-severe-wins priority** | When multiple red flags fire, the patient should be triaged at the highest acuity. Under-triage is dangerous; over-triage is safe. |
| **Fail-safe escalation on error** | In a clinical context, a system error should never result in a patient being under-triaged. Escalating to KTAS 1 ensures human review. |
| **Separate symptom extraction from rule evaluation** | Allows reuse of extracted symptoms across all rules (extract once, evaluate many), and makes each component independently testable. |
| **Optional pain_score and age** | Not all presentations include pain scores or age. Rules with these conditions silently skip when the data is absent, rather than failing. |
| **Safety layer before ML model** | Deterministic safety checks are computationally cheap and clinically critical. Running them first avoids unnecessary model inference for obvious emergencies. |
