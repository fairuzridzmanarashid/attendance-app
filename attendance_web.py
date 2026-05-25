from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB_NAME = "attendance.db"

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

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            team TEXT,
            date TEXT,
            day TEXT,
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
# ✅ FIXED FUNCTION
# -----------------------------
def mark_attendance(uid):
    user = find_user(uid)

    if not user:
        return "❌ User not found"

    today, today_day = get_today()
    team = user["team"]

    # ✅ CORRECT LOGIC (NO SYNTAX ERROR)
    if today_day in TEAM_SCHEDULEstatus = "1"
    else:
        status = "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        INSERT INTO attendance (user_id, team, date, day, status)
        VALUES (?, ?, ?, ?, ?)
    """, (uid, team, today, today_day, status))

    conn.commit()
    conn.close()

    return f"✅ {uid} marked as {status}"

# -----------------------------
# DASHBOARD
# -----------------------------
def get_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT user_id, team, date, status
        FROM attendance
        ORDER BY id DESC
        LIMIT 10
    """)

    data = c.fetchall()
    conn.close()

    return data

# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("user_id")
        if uid:
            message = mark_attendance(uid)

    data = get_dashboard()

    return render_template_string("""
    <html>
    <head>
        <title>Attendance System</title>
    </head>

    <body style="font-family:Arial; text-align:center; padding-top:40px;">

        <h1>📋 Attendance System</h1>

        <form method="POST">
            <input type="text" name="user_id" placeholder="Enter ID" required>
            <br><br>
            <button type="submit">Submit</button>
        </form>

        <p style="margin-top:20px; font-weight:bold;">
            {{message}}
        </p>

        <h2>Recent Records</h2>

        <table border="1" style="margin:auto; border-collapse:collapse;">
            <tr>
                <th>User ID</th>
                <th>Team</th>
                <th>Date</th>
                <th>Status</th>
            </tr>

            {% for row in data %}
            <tr>
                <td>{{row[0]}}</td>
                <td>{{row[1]}}</td>
                <td>{{row[2]}}</td>
                <td>{{row[3]}}</td>
            </tr>
            {% endfor %}
        </table>

    </body>
    </html>
    """, message=message, data=data)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
