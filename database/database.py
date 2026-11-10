import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "debug_history.db")

def init_db():
    """Initializes the SQLite database and creates the debug_sessions table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS debug_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        title TEXT,
        source_code TEXT NOT NULL,
        error_log TEXT NOT NULL,
        bug_category TEXT,
        root_cause TEXT,
        fixed_code TEXT,
        verification_status TEXT,
        iterations INTEGER,
        language TEXT DEFAULT 'Python',
        project_name TEXT DEFAULT 'Single File'
    )
    """)
    
    # Safely migration check for existing DBs
    cursor.execute("PRAGMA table_info(debug_sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    if "language" not in columns:
        cursor.execute("ALTER TABLE debug_sessions ADD COLUMN language TEXT DEFAULT 'Python'")
    if "project_name" not in columns:
        cursor.execute("ALTER TABLE debug_sessions ADD COLUMN project_name TEXT DEFAULT 'Single File'")

    conn.commit()
    conn.close()

def save_debug_session(
    title: str,
    source_code: str,
    error_log: str,
    bug_category: str,
    root_cause: str,
    fixed_code: str,
    verification_status: str,
    iterations: int,
    language: str = "Python",
    project_name: str = "Single File"
) -> int:
    """Saves a new debugging session record into SQLite database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO debug_sessions (
        timestamp, title, source_code, error_log, bug_category, root_cause, fixed_code, verification_status, iterations, language, project_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, title, source_code, error_log, bug_category, root_cause, fixed_code, verification_status, iterations, language, project_name
    ))

    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_all_sessions() -> List[Dict[str, Any]]:
    """Retrieves all historical debugging sessions from SQLite database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM debug_sessions ORDER BY id DESC")
    rows = cursor.fetchall()

    sessions = [dict(row) for row in rows]
    conn.close()
    return sessions
