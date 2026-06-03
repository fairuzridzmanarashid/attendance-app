from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import os
import pandas as pd

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

TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"]
}

DB_NAME = "attendance.db"

# -----------------------------
# INIT DB
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT
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
    return next((u for u in EMPLOYEES if u["id"] == uid), None)

# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    today, _ = get_today()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT 1 FROM attendance WHERE user_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "Already scanned"

    c.execute("INSERT INTO attendance (user_id, date) VALUES (?, ?)", (uid, today))
    conn.commit()
    conn.close()
    return "Scan successful"

# -----------------------------
# DASHBOARD (WITH OT + NI)
# -----------------------------
def get_dashboard():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    result = []

    for user in EMPLOYEES:
        uid = user["id"]
        team = user["team"]

        working_days = TEAM_SCHEDULE[team]
        is_working = today_day in working_days

        c.execute("SELECT 1 FROM attendance WHERE user_id=? AND date=?", (uid, today))
        scanned = c.fetchone() is not None

        if is_working and scanned:
            status = "1"
        elif not is_working and scanned:
            status = "OT"
        elif is_working and not scanned:
            status = "NI"
        else:
            status = "OFF"

        result.append({
            "id": uid,
            "team": team,
            "date": today,
            "day": today_day,
            "status": status
        })

    conn.close()
    return result

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1":0, "OT":0, "NI":0, "OFF":0}
    for r in data:
        summary[r["status"]] += 1
    return summary

# -----------------------------
# ✅ EXPORT EXCEL (FIXED 100%)
# -----------------------------
@app.route("/export")
def export_excel():
    data = get_dashboard()
    df = pd.DataFrame(data)

    # Add filename with date
    today = datetime.now().strftime("%Y%m%d")
    filename = f"attendance_{today}.xlsx"

    filepath = os.path.join(os.getcwd(), filename)
    df.to_excel(filepath, index=False)

    return send_file(filepath, as_attachment=True)

# -----------------------------
# WEB UI (✅ FIXED BUTTON + GUI)
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("uid")
        if find_user(uid):
            message = mark_attendance(uid)
        else:
            message = "Invalid ID"

    data = get_dashboard()
    summary = get_summary(data)
    today, today_day = get_today()

    return render_template_string("""
    <html>
    <head>
        <title>Attendance System</title>
        <style>
            body { font-family: Arial; text-align: center; background:#f5f5f5; }
            .box { background:white; padding:20px; margin:20px auto; width:80%; border-radius:10px; }
            table { border-collapse: collapse; width:100%; }
            th, td { padding:10px; border:1px solid #ddd; }
            th { background:#007BFF; color:white; }
            .btn { padding:12px 25px; background:#007BFF; color:white; border:none; border-radius:8px; font-size:16px; cursor:pointer; }
            .btn:hover { background:#0056b3; }
        </style>
    </head>

    <body>

    <div class="box">
        <h2>Attendance System</h2>
        <h4>{{today}} ({{today_day}})</h4>

        <form method="POST">
            <input name="uid" placeholder="Scan ID" required>
            <button class="btn">Submit</button>
        </form>

        <p><b>{{message}}</b></p>

        <h3>Summary</h3>
        <p>
            1: {{summary["1"]}} |
            OT: {{summary["OT"]}} |
            NI: {{summary["NI"]}} |
            OFF: {{summary["OFF"]}}
        </p>

        <h3>Dashboard</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Team</th>
                <th>Date</th>
                <th>Day</th>
                <th>Status</th>
            </tr>

            {% for r in data %}
            <tr>
                <td>{{r.id}}</td>
                <td>{{r.team}}</td>
                <td>{{r.date}}</td>
                <td>{{r.day}}</td>
                <td><b>{{r.status}}</b></td>
            </tr>
            {% endfor %}
        </table>

        <br><br>

        <!-- ✅ FIXED EXPORT BUTTON -->
        /export
            <button class="btn">⬇ Export Excel</button>
        </a>

    </div>

    </body>
    </html>
    """, message=message, data=data, summary=summary, today=today, today_day=today_day)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
