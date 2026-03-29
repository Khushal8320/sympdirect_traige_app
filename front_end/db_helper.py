

import bcrypt
from database import get_connection

def create_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    cursor.execute("""
        INSERT INTO users (email, password_hash)
        VALUES (?, ?)
    """, (email, password_hash))

    conn.commit()
    conn.close()

def login_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, password_hash
        FROM users
        WHERE email = ?
    """, (email,))

    result = cursor.fetchone()
    conn.close()

    if result:
        user_id, stored_hash = result
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")):
            return user_id

    return None

def save_assessment(user_id, sex, age, chief_complaint, sbp, dbp, rr, temp, nrs_pain, heart_rate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assessments (
            user_id, sex, age, chief_complaint, sbp, dbp, rr, temp, nrs_pain, heart_rate
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, sex, age, chief_complaint, sbp, dbp, rr, temp, nrs_pain, heart_rate))

    assessment_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return assessment_id