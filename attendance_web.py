from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd

app = Flask(__name__)

DB_NAME = "attendance.db"

# ✅ TEAM-BASED SCHEDULE (FIXED)
TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"]
}

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            shift TEXT,
            team TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id TEXT,
            date TEXT,
            status TEXT,
            UNIQUE(id, date)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# HELPERS
# -----------------------------
def get_today():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%A")


def format_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%a')} {dt.day}/{dt.month}"


def get_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = c.fetchone()
    conn.close()
    return user


# -----------------------------
# ADD USER
# -----------------------------
def add_user(name, uid, shift, team):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (uid, name, shift, team))
        conn.commit()
        msg = "✅ User added"
    except:
        msg = "❌ User already exists"
    conn.close()
    return msg


# -----------------------------
# REMOVE USER
# -----------------------------
def remove_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return "🗑 User removed"


# -----------------------------
# AUTO OFF / NI (TEAM LOGIC)
# -----------------------------
def auto_mark_absent(selected_date):
    dt = datetime.strptime(selected_date, "%Y-%m-%d")
    today_day = dt.strftime("%A")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    for u in users:
        uid = u[0]
        team = u[3]   # ✅ USE TEAM

        c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, selected_date))
        record = c.fetchone()

        if not record:
            working_days = TEAM_SCHEDULE[team]

            if today_day in working_days:
                status = "NI"
            else:
                status = "OFF"

            c.execute("INSERT INTO attendance VALUES (?, ?, ?)", (uid, selected_date, status))

    conn.commit()
    conn.close()


# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    user = get_user(uid)

    if not user:
        return "❌ User not found"

    today_date, today_day = get_today()
    team = user[3]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, today_date))
    record = c.fetchone()

    working_days = TEAM_SCHEDULE[team]

    if record:
        if record[2] == "OFF":
            c.execute("UPDATE attendance SET status='OT' WHERE id=? AND date=?", (uid, today_date))
            conn.commit()
            conn.close()
            return f"🔥 OT recorded: {user[1]}"

        elif record[2] == "NI":
            c.execute("UPDATE attendance SET status='1' WHERE id=? AND date=?", (uid, today_date))
            conn.commit()
            conn.close()
            return f"✅ Present: {user[1]}"

        else:
            conn.close()
            return "⚠️ Already recorded"

    if today_day in working_days:
        status = "1"
    else:
        status = "OT"

    c.execute("INSERT INTO attendance VALUES (?, ?, ?)", (uid, today_date, status))
    conn.commit()
    conn.close()

    return f"✅ Recorded: {user[1]}"


# -----------------------------
# EXPORT EXCEL (FULL REPORT)
# -----------------------------
def export_excel():
    conn = sqlite3.connect(DB_NAME)

    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    att_df = pd.read_sql_query("SELECT * FROM attendance", conn)

    def format_excel_date(date_str):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.strftime('%a')} {dt.day}/{dt.month}"

