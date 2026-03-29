import sqlite3
import json
import pandas as pd
from datetime import datetime

DB_PATH = "triage_app.db"


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            model_used  TEXT NOT NULL,
            ktas_score  INTEGER NOT NULL,
            recommendation TEXT NOT NULL,
            patient_data   TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_training_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       TEXT NOT NULL,
            model_name      TEXT NOT NULL,
            accuracy        REAL NOT NULL,
            test_size       REAL NOT NULL,
            training_samples INTEGER NOT NULL,
            test_samples    INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_prediction(model_used, ktas_score, recommendation, patient_data: dict):
    """Save a prediction record to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions (timestamp, model_used, ktas_score, recommendation, patient_data)
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model_used,
        int(ktas_score),
        recommendation,
        json.dumps(patient_data)
    ))
    conn.commit()
    conn.close()


def save_training_log(model_name, accuracy, test_size, training_samples, test_samples):
    """Log a model training run."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO model_training_logs (timestamp, model_name, accuracy, test_size, training_samples, test_samples)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        model_name,
        float(accuracy),
        float(test_size),
        int(training_samples),
        int(test_samples)
    ))
    conn.commit()
    conn.close()


def get_all_predictions():
    """Return all predictions as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, timestamp, model_used, ktas_score, recommendation FROM predictions ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


def get_prediction_detail(prediction_id):
    """Return full patient data for a single prediction."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_data FROM predictions WHERE id = ?", (prediction_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return {}


def get_training_logs():
    """Return all training logs as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM model_training_logs ORDER BY id DESC",
        conn
    )
    conn.close()
    return df


def delete_prediction(prediction_id):
    """Delete a prediction record by id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM predictions WHERE id = ?", (prediction_id,))
    conn.commit()
    conn.close()


def get_prediction_stats():
    """Return summary stats for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM predictions")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT ktas_score, COUNT(*) as cnt FROM predictions GROUP BY ktas_score ORDER BY ktas_score")
    by_ktas = cursor.fetchall()

    cursor.execute("SELECT model_used, COUNT(*) as cnt FROM predictions GROUP BY model_used")
    by_model = cursor.fetchall()

    conn.close()
    return {
        "total": total,
        "by_ktas": by_ktas,
        "by_model": by_model
    }
