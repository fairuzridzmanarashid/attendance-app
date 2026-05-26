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
    {"id": "7363", "team": "C"},
]

# -----------------------------
# TEAM SCHEDULE
# -----------------------------
TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"],
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT,
            day TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

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
        return "User not found ❌"

    today, today_day = get_today()
    team = user["team"]

    if today_day in TEAM_SCHEDULEstatus = "1"
    else:
        status = "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Check if already marked
    c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "Already marked today ✅"

    c.execute(
        "INSERT INTO attendance (user_id, date, day, status) VALUES (?, ?, ?, ?)",
        (uid, today, today_day, status)
    )

    conn.commit()
    conn.close()

    return f"Marked {status} for {uid} ✅"

# -----------------------------
# DASHBOARD
# -----------------------------
def get_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT user_id, date, status FROM attendance ORDER BY date DESC")
    rows = c.fetchall()

    conn.close()
    return rows

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1": 0, "OT": 0, "OFF": 0}

    for row in data:
        status = row[2]
        if status in summary:
            summary[status] += 1

    return summary

# -----------------------------
# WEB UI
# -----------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Attendance App</title>
</head>
<body>
    <h1>Attendance System ✅</h1>

    <form method="POST">
        <input type="text" name="user_id" placeholder="Enter ID" required>
        <button type="submit">Mark Attendance</button>
    </form>

    <p>{{ message }}</p>

    <h2>Dashboard</h2>
    <table border="1">
        <tr>
            <th>User ID</th>
            <th>Date</th>
            <th>Status</th>
        </tr>
        {% for row in data %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
            <td>{{ row[2] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("user_id")
        message = mark_attendance(uid)

    data = get_dashboard()
    return render_template_string(HTML_TEMPLATE, message=message, data=data)

# -----------------------------
# RUN (Render Ready)
# -----------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
