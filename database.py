import sqlite3
from contextlib import contextmanager
from typing import Optional

DB_PATH = "posted.db"


@contextmanager
def get_conn():
    """
    Create and safely close a database connection.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """
    Initialize database tables.
    """
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                link TEXT PRIMARY KEY
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                mode TEXT NOT NULL,
                winner TEXT NOT NULL,
                score TEXT NOT NULL,
                mvp TEXT NOT NULL
            )
        """)

        conn.commit()


def already_posted(link: str) -> bool:
    """
    Check if a link already exists in the posts table.
    """
    with get_conn() as conn:
        cursor = conn.execute(
            "SELECT 1 FROM posts WHERE link = ?",
            (link,)
        )
        return cursor.fetchone() is not None


def save_post(link: str):
    """
    Save a post link if it does not already exist.
    """
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posts (link) VALUES (?)",
            (link,)
        )
        conn.commit()


def save_scrim_result(
    date: str,
    mode: str,
    winner: str,
    score: str,
    mvp: str
):
    """
    Save a scrim result.
    """
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO scrims (
                date,
                mode,
                winner,
                score,
                mvp
            )
            VALUES (?, ?, ?, ?, ?)
        """, (date, mode, winner, score, mvp))

        conn.commit()


def get_last_scrim() -> Optional[dict]:
    """
    Fetch the latest scrim result.
    """
    with get_conn() as conn:
        cursor = conn.execute("""
            SELECT
                date,
                mode,
                winner,
                score,
                mvp
            FROM scrims
            ORDER BY id DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row:
            return {
                "date": row["date"],
                "mode": row["mode"],
                "winner": row["winner"],
                "score": row["score"],
                "mvp": row["mvp"]
            }

    return None


# Initialize database on startup
init_db()