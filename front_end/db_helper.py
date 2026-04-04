import sqlite3
import bcrypt
from database import get_connection


def create_user(email, password):
    """
    Insert a new user. Returns True on success, False if the email already exists.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Email already registered (UNIQUE constraint)
        return False
    finally:
        conn.close()


def login_user(email, password):
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, password_hash FROM users WHERE email = ?",
        (email,),
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        user_id, stored_hash = result
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return user_id
    return None


def save_assessment(
    user_id, sex, age, chief_complaint,
    sbp, dbp, rr, temp, nrs_pain, heart_rate,
    # Core prediction
    predicted_ctas=None, final_ctas=None, confidence_score=None,
    # Explainable-AI fields
    pregnancy_rule_ctas=None, clinical_rule_ctas=None, combined_rule_ctas=None,
    model_default_ctas=None,  model_tuned_ctas=None,  final_source=None,
):
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assessments (
            user_id, sex, age, chief_complaint,
            sbp, dbp, rr, temp, nrs_pain, heart_rate,
            predicted_ctas, final_ctas, confidence_score,
            pregnancy_rule_ctas, clinical_rule_ctas, combined_rule_ctas,
            model_default_ctas,  model_tuned_ctas,  final_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, sex, age, chief_complaint,
        sbp, dbp, rr, temp, nrs_pain, heart_rate,
        predicted_ctas, final_ctas, confidence_score,
        pregnancy_rule_ctas, clinical_rule_ctas, combined_rule_ctas,
        model_default_ctas,  model_tuned_ctas,  final_source,
    ))

    conn.commit()
    assessment_id = cursor.lastrowid
    conn.close()
    return assessment_id


def get_user_id_by_email(email):
    """Return user_id for a given email, or None if not found."""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def save_result(
    assessment_id,
    predicted_ctas=None, final_ctas=None, confidence_score=None,
    pregnancy_rule_ctas=None, clinical_rule_ctas=None, combined_rule_ctas=None,
    model_default_ctas=None, model_tuned_ctas=None, final_source=None,
):
    """
    Save prediction outputs to the results table, linked to an assessment row.
    Returns the new result_id.
    """
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO results (
            assessment_id,
            predicted_ctas, final_ctas, confidence_score,
            pregnancy_rule_ctas, clinical_rule_ctas, combined_rule_ctas,
            model_default_ctas,  model_tuned_ctas,  final_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        assessment_id,
        predicted_ctas, final_ctas, confidence_score,
        pregnancy_rule_ctas, clinical_rule_ctas, combined_rule_ctas,
        model_default_ctas,  model_tuned_ctas,  final_source,
    ))

    conn.commit()
    result_id = cursor.lastrowid
    conn.close()
    return result_id