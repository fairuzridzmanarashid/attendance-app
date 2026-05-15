from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# EMPLOYEES (SAFE - NO EXCEL)
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

# ✅ SAME SCHEDULE
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
        return "❌ ID NOT FOUND"

    today, today_day = get_today()
    team = user["team"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Check if already exists
    c.execute(
        "SELECT status FROM attendance WHERE id=? AND date=?",
        (uid, today)
    )
    existing = c.fetchone()

    # -------------------------
    # WORKING LOGIC
    # -------------------------

    if today_day not in TEAM_SCHEDULE.get(team, []):
        status = "OT" if not existing else "OT"
    else:
        status = "1" if not existing else existing[0]

    if existing:
        conn.close()
        return f"⚠️ ALREADY: {existing[0]}"

    c.execute(
        "INSERT INTO attendance (id, date, status) VALUES (?, ?, ?)",
        (uid, today, status)
    )

    conn.commit()
    conn.close()

    if status == "1":
        return "✅ PRESENT"
    else:
        return "🔵 OT RECORDED"

# -----------------------------
# DASHBOARD
# -----------------------------
def get_dashboard():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    results = []

    for u in EMPLOYEES:
        uid = u["id"]
        team = u["team"]

        c.execute(
            "SELECT status FROM attendance WHERE id=? AND date=?",
            (uid, today)
        )
        rec = c.fetchone()

        if rec:
            status = rec[0]
        else:
            if today_day in TEAM_SCHEDULE.get(team, []):
                status = "NI"
            else:
                status = "OFF"

        results.append({
            "id": uid,
            "team": team,
            "status": status
        })

    conn.close()
    return results

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary(data):
    summary = {"1":0, "OT":0, "OFF":0, "NI":0}

    for r in data:
        summary[r["status"]] += 1

    return summary

# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form["id"]
        message = mark_attendance(uid)

    data = get_dashboard()
    summary = get_summary(data)

    html = """
    <html>
    <head>
        <title>Attendance</title>
        <style>
            body { font-family: Arial; text-align:center; }
            input { font-size:28px; padding:10px; }
            button { font-size:24px; padding:10px; }
            table { border-collapse: collapse; margin:auto; }
            th, td { border:1px solid black; padding:8px; }

            .1 { background:lightgreen; }
            .OT { background:lightblue; }
            .OFF { background:#ffeeba; }
            .NI { background:#f8d7da; }
        </style>
    </head>

    <body>

    <h1>Attendance System</h1>

    <form method="POST">
        <input name="id" placeholder="Enter ID Badge" autofocus>
        <br><br>
        <button type="submit">Submit</button>
    </form>

    <h2>{{message}}</h2>

    <h3>Summary</h3>
    ✅ {{summary["1"]}} |
    🔵 {{summary["OT"]}} |
    🟡 {{summary["OFF"]}} |
    🔴 {{summary["NI"]}}

    <h3>Today</h3>

    <table>
        <tr><th>ID</th><th>Team</th><th>Status</th></tr>
        {% for r in data %}
        <tr class="{{r.status}}">
            <td>{{r.id}}</td>
            <td>{{r.team}}</td>
            <td>{{r.status}}</td>
        </tr>
        {% endfor %}
    </table>

    </body>
    </html>
    """

    return render_template_string(html, data=data, summary=summary, message=message)

# -----------------------------
# RUN (Render ready)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)