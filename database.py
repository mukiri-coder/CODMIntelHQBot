import sqlite3

conn = sqlite3.connect("posted.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS posts (
    link TEXT PRIMARY KEY
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS scrims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    mode TEXT,
    winner TEXT,
    score TEXT,
    mvp TEXT
)
''')

conn.commit()


def already_posted(link):
    cursor.execute("SELECT link FROM posts WHERE link=?", (link,))
    return cursor.fetchone() is not None


def save_post(link):
    cursor.execute("INSERT OR IGNORE INTO posts(link) VALUES(?)", (link,))
    conn.commit()


def save_scrim_result(date, mode, winner, score, mvp):
    cursor.execute(
        "INSERT INTO scrims(date, mode, winner, score, mvp) VALUES(?,?,?,?,?)",
        (date, mode, winner, score, mvp)
    )
    conn.commit()


def get_last_scrim():
    cursor.execute("SELECT * FROM scrims ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        return {"date": row[1], "mode": row[2], "winner": row[3], "score": row[4], "mvp": row[5]}
    return None