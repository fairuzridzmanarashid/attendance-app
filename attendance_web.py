from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# EMPLOYEES
# -----------------------------
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

# TEAM SCHEDULE
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

    today, today_day = get_today()

    if today_day in TEAM_SCHEDULE[user["team"]]:
        status = "1"
    else:
        status = "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO attendance VALUES (?, ?, ?)", (uid, today, status))
    conn.commit()
    conn.close()

    return f"Attendance recorded: {status}"

# -----------------------------
# DASHBOARD
# -----------------------------
def get_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, status FROM attendance")
    data = c.fetchall()
    conn.close()
    return data

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1": 0, "OFF": 0}

    for row in data:
        status = row[1]
        if status in summary:
            summary[status] += 1

    return summary

# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("uid")
        message = mark_attendance(uid)

    data = get_dashboard()
    summary = get_summary(data)

    html = """
    <h2>Attendance System</h2>

    <form method="POST">
        Employee ID: <input name="uid">
        <button type="submit">Mark Attendance</button>
    </form>

    <p>{{message}}</p>

    <h3>Summary</h3>
    <p>Present: {{summary['1']}}</p>
    <p>Off: {{summary['OFF']}}</p>

    <h3>Records</h3>
    <ul>
    {% for row in data %}
        <li>{{row[0]}} - {{row[1]}}</li>
    {% endfor %}
    </ul>
    """

    return render_template_string(html, message=message, summary=summary, data=data)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
