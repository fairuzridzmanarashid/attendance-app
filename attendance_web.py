from flask import Flask, request, render_template_string
import sqlite3
from datetime import datetime

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

# ✅ INIT DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            date TEXT,
            status TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ✅ HELPERS
def get_today():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%A")

def find_user(uid):
    for u in EMPLOYEES:
        if u["id"] == uid:
            return u
    return None

# ✅ MARK ATTENDANCE
def mark_attendance(uid):
    user = find_user(uid)
    if not user:
        return "User not found"

    today, today_day = get_today()

    is_work_day = today_day in TEAM_SCHEDULE[user["team"]]
    status = "1" if is_work_day else "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # prevent duplicate
    c.execute("SELECT * FROM attendance WHERE emp_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "Already marked today"

    c.execute(
        "INSERT INTO attendance (emp_id, date, status, time) VALUES (?, ?, ?, ?)",
        (uid, today, status, datetime.now().strftime("%H:%M:%S"))
    )
    conn.commit()
    conn.close()

    return "Attendance recorded"

# ✅ DASHBOARD
def get_dashboard():
    today, _ = get_today()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT emp_id, status, time FROM attendance WHERE date=?", (today,))
    data = c.fetchall()

    conn.close()
    return data

# ✅ SUMMARY
def get_summary(data):
    summary = {"1": 0, "OFF": 0}

    for row in data:
        summary[row[1]] += 1

    return summary

# ✅ UI
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
        <input name="uid" placeholder="Enter Employee ID" required>
        <button type="submit">Submit</button>
    </form>

    <p>{{message}}</p>

    <h3>Summary</h3>
    Present: {{summary["1"]}} <br>
    OFF: {{summary["OFF"]}}

    <h3>Today Records</h3>
    <table border="1">
        <tr><th>ID</th><th>Status</th><th>Time</th></tr>
        {% for r in data %}
        <tr>
            <td>{{r[0]}}</td>
            <td>{{r[1]}}</td>
            <td>{{r[2]}}</td>
        </tr>
        {% endfor %}
    </table>
    """

    return render_template_string(html, data=data, summary=summary, message=message)

# ✅ RUN
if __name__ == "__main__":
    app.run(debug=True)
