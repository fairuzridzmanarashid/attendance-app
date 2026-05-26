from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd

app = Flask(__name__)
DB_NAME = "attendance.db"

# ✅ INIT DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Employees table
    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT
        )
    """)

    # Attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT,
            name TEXT,
            date TEXT,
            day TEXT,
            status TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

TEAM_SCHEDULE = {
    "A": ["Sunday", "Monday", "Tuesday", "Wednesday"],
    "B": ["Wednesday", "Thursday", "Friday", "Saturday"],
    "C": ["Monday", "Tuesday", "Thursday", "Friday"]
}

# ✅ HELPERS
def get_today():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%A")

def find_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM employees WHERE id=?", (uid,))
    user = c.fetchone()
    conn.close()
    return user

# ✅ ADD USER
def add_user(uid, name, team):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("INSERT OR IGNORE INTO employees VALUES (?, ?, ?)", (uid, name, team))

    conn.commit()
    conn.close()
    return "User added"

# ✅ REMOVE USER
def remove_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("DELETE FROM employees WHERE id=?", (uid,))
    conn.commit()
    conn.close()

    return "User removed"

# ✅ MARK ATTENDANCE
def mark_attendance(uid):
    user = find_user(uid)
    if not user:
        return "User not found"

    emp_id, name, team = user
    today, today_day = get_today()

    is_work_day = today_day in TEAM_SCHEDULE.get(team, [])
    status = "1" if is_work_day else "OFF"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # prevent duplicate
    c.execute("SELECT * FROM attendance WHERE emp_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "Already marked"

    c.execute("""
        INSERT INTO attendance (emp_id, name, date, day, status, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (emp_id, name, today, today_day, status,
          datetime.now().strftime("%H:%M:%S")))

    conn.commit()
    conn.close()

    return "Attendance recorded"

# ✅ GET DATA
def get_dashboard():
    today, _ = get_today()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, emp_id, date, status FROM attendance WHERE date=?", (today,))
    rows = c.fetchall()

    conn.close()
    return rows

# ✅ EXPORT EXCEL
@app.route("/export")
def export_excel():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT name AS 'Name', emp_id AS 'ID Badge', date AS 'Date', status AS 'Status' FROM attendance", conn)
    conn.close()

    file = "attendance.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# ✅ MAIN UI
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    today, today_day = get_today()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "mark":
            message = mark_attendance(request.form.get("uid"))

        elif action == "add":
            message = add_user(
                request.form.get("uid"),
                request.form.get("name"),
                request.form.get("team")
            )

        elif action == "remove":
            message = remove_user(request.form.get("uid"))

    data = get_dashboard()

    html = """
    <h1>📋 Attendance System</h1>

    <h3>Today: {{today}} ({{today_day}})</h3>

    <p style="color:green;">{{message}}</p>

    <hr>

    <h3>✅ Mark Attendance</h3>
    <form method="POST">
        <input name="uid" placeholder="ID Badge" required>
        <button name="action" value="mark">Submit</button>
    </form>

    <hr>

    <h3>👤 Add User</h3>
    <form method="POST">
        <input name="name" placeholder="Name" required>
        <input name="uid" placeholder="ID Badge" required>
        <select name="team">
            <option>A</option>
            <option>B</option>
            <option>C</option>
        </select>
        <button name="action" value="add">Add User</button>
    </form>

    <hr>

    <h3>❌ Remove User</h3>
    <form method="POST">
        <input name="uid" placeholder="ID Badge" required>
        <button name="action" value="remove">Remove</button>
    </form>

    <hr>

    <h3>📊 Records</h3>
    <table border="1" cellpadding="5">
        <tr>
            <th>Name</th>
            <th>ID Badge</th>
            <th>Date</th>
            <th>Status</th>
        </tr>
        {% for r in data %}
        <tr>
            <td>{{r[0]}}</td>
            <td>{{r[1]}}</td>
            <td>{{r[2]}}</td>
            <td>{{r[3]}}</td>
        </tr>
        {% endfor %}
    </table>

    <br>

    /export
    """

    return render_template_string(html,
                                  today=today,
                                  today_day=today_day,
                                  data=data,
                                  message=message)

# ✅ RUN
if __name__ == "__main__":
    app.run(debug=True)
