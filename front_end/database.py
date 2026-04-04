import sqlite3

database_name = "triage_ai.db"


def get_connection():
    conn = sqlite3.connect(database_name, check_same_thread=False)
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        email          TEXT NOT NULL UNIQUE,
        password_hash  TEXT NOT NULL,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER,
        sex                 TEXT,
        age                 INTEGER,
        chief_complaint     TEXT,
        sbp                 INTEGER,
        dbp                 INTEGER,
        rr                  INTEGER,
        temp                REAL,
        nrs_pain            INTEGER,
        heart_rate          INTEGER,
        predicted_ctas      INTEGER,
        final_ctas          INTEGER,
        confidence_score    REAL,
        -- Explainable-AI columns
        pregnancy_rule_ctas INTEGER,
        clinical_rule_ctas  INTEGER,
        combined_rule_ctas  INTEGER,
        model_default_ctas  INTEGER,
        model_tuned_ctas    INTEGER,
        final_source        TEXT,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Results table (prediction outputs, linked to assessments) ─────────────
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        result_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id       INTEGER NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
        predicted_ctas      INTEGER,
        final_ctas          INTEGER,
        confidence_score    REAL,
        pregnancy_rule_ctas INTEGER,
        clinical_rule_ctas  INTEGER,
        combined_rule_ctas  INTEGER,
        model_default_ctas  INTEGER,
        model_tuned_ctas    INTEGER,
        final_source        TEXT,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Non-destructive migration: add XAI columns if they were missing ────────
    _xai_columns = [
        ("pregnancy_rule_ctas", "INTEGER"),
        ("clinical_rule_ctas",  "INTEGER"),
        ("combined_rule_ctas",  "INTEGER"),
        ("model_default_ctas",  "INTEGER"),
        ("model_tuned_ctas",    "INTEGER"),
        ("final_source",        "TEXT"),
    ]
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(assessments)")}
    for col, col_type in _xai_columns:
        if col not in existing:
            cursor.execute(f"ALTER TABLE assessments ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()