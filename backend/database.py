import sqlite3
import json

conn = sqlite3.connect("data/interviews.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS interview_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    job_role TEXT,
    priority_index INTEGER,
    jd_priority TEXT,
    question_number INTEGER,
    question_type TEXT,
    satisfaction REAL,
    confidence TEXT,
    strengths TEXT,
    weaknesses TEXT,
    timestamp DATETIME,
    question TEXT,
    answer TEXT
)
""")

conn.commit()
print("Database initialized and table created if not exists.")

def save_turn(record):
    cursor.execute(
        """
        INSERT INTO interview_turns
        (
        session_id,
        job_role,
        priority_index,
        jd_priority,
        question_number,
        question_type,
        satisfaction,
        confidence,
        strengths,
        weaknesses,
        timestamp,
        question,
        answer
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["session_id"],
            record["job_role"],
            record["priority_index"],
            record["jd_priority"],
            record["question_number"],
            record["question_type"],
            record["satisfaction"],
            record["confidence"],
            json.dumps(record["strengths"]),
            json.dumps(record["weaknesses"]),
            record["timestamp"],
            record["question"],
            record["answer"]
        )
    )

    conn.commit()