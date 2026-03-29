import sqlite3

database_name="triage_ai.db"

def get_connection():
    conn = sqlite3.connect(database_name, check_same_thread=False)
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sex TEXT NOT NULL,
        age INTEGER NOT NULL,
        chief_complaint TEXT NOT NULL,
        sbp INTEGER,
        dbp INTEGER,
        rr INTEGER,
        temp REAL,
        nrs_pain INTEGER,
        heart_rate INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    conn.commit()
    conn.close()