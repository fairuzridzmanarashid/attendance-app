from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

EMPLOYEES = [
    {"id": "16320", "team": "A"},
    {"id": "7274", "team": "A"},
    {"id": "20346", "team": "A"},
    {"id": "7333", "team": "B"},
    {"id": "15766", "team": "B"},
    {"id": "19555", "team": "B"},
    {"id": "7370", "team": "C"},
    {"id": "7363", "team": "C"}
]

TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"]
}

DB_NAME = "attendance.db"

# -----------------------------
# DATABASE INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id TEXT,
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


def find_user(uid):
    for u in EMPLOYEES:
        if u["id"] == uid:
            return u
    return None


# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    user = find_user(uid)
    if not user:
        return "User not found"

    today, day_name = get_today()
    team_days = TEAM_SCHEDULE[user["team"]]

    status = "1" if day_name in team_days else "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO attendance VALUES (?, ?, ?)", (uid, today, status))
    conn.commit()
    conn.close()

    return f"Attendance marked: {uid} = {status}"


# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("uid")
        message = mark_attendance(uid)

    return render_template_string("""
        <h2>Attendance System</h2>
        <form method="post">
            Employee ID: <input name="uid">
            <button type="submit">Submit</button>
        </form>
        <p>{{message}}</p>
    """, message=message)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
