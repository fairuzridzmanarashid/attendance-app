from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import os
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side

app = Flask(__name__)

DB_NAME = "attendance.db"

# -----------------------------
# TEAM SCHEDULE
# -----------------------------
TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"]
}

# -----------------------------
# DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT,
            shift TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            team TEXT,
            date TEXT,
            status TEXT
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

def is_work_day(team, day):
    return day in TEAM_SCHEDULE.get(team, [])

# -----------------------------
# USER FUNCTIONS
# -----------------------------
def add_user(uid, name, team, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                  (uid, name, team, shift))
        conn.commit()
        msg = "Added"
    except:
        msg = "Exists"
    conn.close()
    return msg

def update_user(uid, name, team, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET name=?, team=?, shift=? WHERE user_id=?",
              (name, team, shift, uid))
    conn.commit()
    conn.close()
    return "Updated"

def remove_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit()
    msg = "Deleted" if c.rowcount else "Not found"
    conn.close()
    return msg

def find_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, team FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "team": row[2]}
    return None

def get_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, team, shift FROM users")
    data = c.fetchall()
    conn.close()
    return data

# -----------------------------
# ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    today, today_day = get_today()
    user = find_user(uid)

    if not user:
        return "NI"

    team = user["team"]
    status = "1" if is_work_day(team, today_day) else "OT"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT status FROM attendance WHERE user_id=? AND date=?", (uid, today))
    exist = c.fetchone()

    if exist:
        conn.close()
        return exist[0]

    c.execute(
        "INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
        (uid, team, today, status)
    )

    conn.commit()
    conn.close()

    return status

def fill_absent():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    users = get_users()

    for u in users:
        uid, name, team, shift = u

        c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
        if c.fetchone():
            continue

        status = "NI" if is_work_day(team, today_day) else "OFF"

        c.execute(
            "INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
            (uid, team, today, status)
        )

    conn.commit()
    conn.close()

def get_dashboard():
    fill_absent()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT a.user_id, u.name, a.team, a.date, a.status
        FROM attendance a
        LEFT JOIN users u ON a.user_id = u.user_id
        ORDER BY a.id DESC
    """)

    data = c.fetchall()
    conn.close()
    return data

def get_summary(data):
    summary = {"1":0,"OT":0,"NI":0,"OFF":0}
    for r in data:
        if r[4] in summary:
            summary[r[4]] += 1
    return summary

# -----------------------------
# EXPORT EXCEL
# -----------------------------
@app.route("/export")
def export():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT a.user_id, u.name, a.team, a.date, a.status
        FROM attendance a
        LEFT JOIN users u ON a.user_id = u.user_id
    """)

    rows = c.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active

    headers = ["ID", "Name", "Team", "Date", "Status"]
    ws.append(headers)

    for row in rows:
        ws.append(row)

    align = Alignment(horizontal="center", vertical="center")
    border = Border(left=Side(style="thin"),
                    right=Side(style="thin"),
                    top=Side(style="thin"),
                    bottom=Side(style="thin"))

    for row in ws.iter_rows():
        for cell in row:
