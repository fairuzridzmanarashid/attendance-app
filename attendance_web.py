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

# -----------------------------
# TEAM SCHEDULE
# -----------------------------
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
    for u in EMPLOYEES:
        if u["id"] == uid:
            return u
    return None


# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    today, _ = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Prevent duplicate scan
    c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "Already scanned"

    c.execute("INSERT INTO attendance (user_id, date) VALUES (?, ?)", (uid, today))
    conn.commit()
    conn.close()
    return "Scan successful"


# -----------------------------
# DASHBOARD LOGIC (OT + NI ADDED)
# -----------------------------
def get_dashboard():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    result = []

    for user in EMPLOYEES:
        uid = user["id"]
        team = user["team"]

        working_days = TEAM_SCHEDULE.get(team, [])
        is_working_day = today_day in working_days

        # Check scanned
        c.execute("SELECT 1 FROM attendance WHERE user_id=? AND date=?", (uid, today))
        scanned = c.fetchone() is not None

        # ✅ FINAL STATUS RULE
        if is_working_day and scanned:
            status = "1"
        elif not is_working_day and scanned:
            status = "OT"
        elif is_working_day and not scanned:
            status = "NI"
        else:
            status = "OFF"

        result.append({
            "id": uid,
            "team": team,
            "status": status
        })

    conn.close()
    return result


# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1": 0, "OT": 0, "OFF": 0, "NI": 0}

    for row in data:
        summary[row["status"]] += 1

    return summary


# -----------------------------
# EXPORT EXCEL ✅ FIXED
# -----------------------------
@app.route("/export")
def export_excel():
    data = get_dashboard()

    df = pd.DataFrame(data)

    file_path = "attendance_export.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("uid")
        user = find_user(uid)

        if user:
            message = mark_attendance(uid)
        else:
            message = "Invalid ID"

    data = get_dashboard()
    summary = get_summary(data)

    return render_template_string("""
    <h2>Attendance System</h2>

    <form method="POST">
        <input name="uid" placeholder="Scan ID" required>
        <button type="submit">Submit</button>
    </form>

    <p>{{message}}</p>

    <h3>Summary</h3>
    <ul>
        <li>Present (1): {{summary["1"]}}</li>
        <li>OT: {{summary["OT"]}}</li>
        <li>NI: {{summary["NI"]}}</li>
        <li>OFF: {{summary["OFF"]}}</li>
    </ul>

    <h3>Dashboard</h3>
    <table border="1" cellpadding="5">
        <tr>
            <th>ID</th>
            <th>Team</th>
            <th>Status</th>
        </tr>
        {% for row in data %}
        <tr>
            <td>{{row.id}}</td>
            <td>{{row.team}}</td>
            <td>{{row.status}}</td>
        </tr>
        {% endfor %}
    </table>

    <br>
    /export
        <button style="padding:10px 20px; font-size:16px;">
            ⬇ Export Excel
        </button>
    </a>
    """, message=message, data=data, summary=summary)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
