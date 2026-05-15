from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import os

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
# DATABASE INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            team TEXT,
            date TEXT,
            status TEXT
        )
    """)

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            team TEXT,
            shift TEXT
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

def find_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT user_id, team, shift FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()

    if row:
        return {"id": row[0], "team": row[1], "shift": row[2]}
    return None

# -----------------------------
# USER MANAGEMENT
# -----------------------------
def add_user(user_id, team, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users (user_id, team, shift) VALUES (?, ?, ?)",
                  (user_id, team, shift))
        conn.commit()
        msg = "✅ User added"
    except:
        msg = "⚠️ User already exists"

    conn.close()
    return msg

def remove_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()

    if c.rowcount > 0:
        msg = "🗑 User removed"
    else:
        msg = "❌ User not found"

    conn.close()
    return msg

# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    today, today_day = get_today()
    user = find_user(uid)

    if not user:
        return "❌ User not found"

    team = user["team"]

    if is_work_day(team, today_day):
        status = "1"   # Present
    else:
        status = "OT"  # Overtime

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "⚠️ Already marked today"

    c.execute(
        "INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
        (uid, team, today, status)
    )

    conn.commit()
    conn.close()

    return f"✅ Marked {status}"

# -----------------------------
# AUTO FILL NI (ABSENT)
# -----------------------------
def fill_absent():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT user_id, team FROM users")
    users = c.fetchall()

    for user in users:
        uid, team = user

        c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
        if c.fetchone():
            continue

        if is_work_day(team, today_day):
            status = "NI"
        else:
            status = "OFF"

        c.execute(
            "INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
            (uid, team, today, status)
        )

    conn.commit()
    conn.close()

# -----------------------------
# DASHBOARD
# -----------------------------
def get_dashboard():
    fill_absent()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT user_id, team, date, status FROM attendance ORDER BY id DESC")
    data = c.fetchall()

    conn.close()
    return data

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1": 0, "OT": 0, "NI": 0, "OFF": 0}

    for row in data:
        status = row[3]
        if status in summary:
            summary[status] += 1

    return summary

# -----------------------------
# WEB UI (TABLET STYLE)
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "checkin":
            uid = request.form.get("user_id")
            message = mark_attendance(uid)

        elif action == "add":
            uid = request.form.get("new_id")
            team = request.form.get("team")
            shift = request.form.get("shift")
            message = add_user(uid, team, shift)

        elif action == "remove":
            uid = request.form.get("remove_id")
            message = remove_user(uid)

    data = get_dashboard()
    summary = get_summary(data)

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body { font-family: Arial; background:#f4f6f9; text-align:center; }
.card {
    background:white; padding:20px; margin:20px;
    border-radius:15px; box-shadow:0 4px 10px rgba(0,0,0,0.1);
}
input, select {
    width:90%; padding:15px; margin:5px;
    font-size:20px; border-radius:10px;
}
button {
    width:95%; padding:15px; font-size:20px;
    background:#0078D4; color:white;
    border:none; border-radius:10px;
}
.summary div {
    padding:15px; margin:5px; border-radius:10px;
    font-size:18px; color:white;
}
.present {background:#28a745;}
.ot {background:#ffc107; color:black;}
.ni {background:#dc3545;}
.off {background:#6c757d;}
</style>
</head>

<body>

<h1>📋 Attendance</h1>

<div class="card">
<h2>✅ Check In</h2>
<form method="POST">
    <input name="user_id" placeholder="ID Badge" required autofocus>
    <button name="action" value="checkin">CHECK IN</button>
</form>
</div>

<div class="card">
<h2>➕ Add User</h2>
<form method="POST">
    <input name="new_id" placeholder="ID Badge" required>
    <select name="team">
        <option>A</option><option>B</option><option>C</option>
    </select>
    <select name="shift">
        <option>Morning</option><option>Night</option>
    </select>
    <button name="action" value="add">ADD USER</button>
</form>
</div>

<div class="card">
<h2>🗑 Remove User</h2>
<form method="POST">
    <input name="remove_id" placeholder="ID Badge" required>
    <button name="action" value="remove">DELETE USER</button>
</form>
</div>

<p style="font-size:20px;">{{message}}</p>

<div class="card summary">
<h2>📊 Summary</h2>
<div class="present">✅ {{summary['1']}} Present</div>
<div class="ot">⏱ {{summary['OT']}} OT</div>
<div class="ni">❌ {{summary['NI']}} NI</div>
<div class="off">💤 {{summary['OFF']}} OFF</div>
</div>

</body>
</html>
""", message=message, summary=summary)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
