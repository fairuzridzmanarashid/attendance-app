from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import os
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side

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

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT,
            shift TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            team TEXT,
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

def is_work_day(team, day):
    return day in TEAM_SCHEDULE.get(team, [])

# -----------------------------
# USER FUNCTIONS
# -----------------------------
def add_user(uid, name, team, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                  (uid, name, team, shift))
        conn.commit()
        msg = "✅ User added"
    except:
        msg = "⚠️ User exists"
    conn.close()
    return msg

def update_user(uid, name, team, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET name=?, team=?, shift=? WHERE user_id=?",
              (name, team, shift, uid))
    conn.commit()
    conn.close()
    return "✅ Updated"

def remove_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit()
    msg = "🗑 Deleted" if c.rowcount else "❌ Not found"
    conn.close()
    return msg

def find_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, team FROM users WHERE user_id=?", (uid,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "team": row[2]}
    return None

def get_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, team, shift FROM users")
    data = c.fetchall()
    conn.close()
    return data

# -----------------------------
# ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    today, today_day = get_today()
    user = find_user(uid)

    if not user:
        return "❌ Add user first"

    team = user["team"]

    status = "1" if is_work_day(team, today_day) else "OT"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
    if c.fetchone():
        conn.close()
        return "⚠️ Already marked"

    c.execute("INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
              (uid, team, today, status))

    conn.commit()
    conn.close()
    return f"✅ {user['name']} ({status})"

def fill_absent():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    users = get_users()

    for u in users:
        uid, name, team, shift = u

        c.execute("SELECT * FROM attendance WHERE user_id=? AND date=?", (uid, today))
        if c.fetchone():
            continue

        status = "NI" if is_work_day(team, today_day) else "OFF"

        c.execute("INSERT INTO attendance (user_id, team, date, status) VALUES (?, ?, ?, ?)",
                  (uid, team, today, status))

    conn.commit()
    conn.close()

def get_dashboard():
    fill_absent()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT a.user_id, u.name, a.team, a.date, a.status
        FROM attendance a
        LEFT JOIN users u ON a.user_id = u.user_id
        ORDER BY a.id DESC
    """)

    data = c.fetchall()
    conn.close()
    return data

def get_summary(data):
    summary = {"1":0,"OT":0,"NI":0,"OFF":0}
    for r in data:
        if r[4] in summary:
            summary[r[4]] += 1
    return summary

# -----------------------------
# EXPORT EXCEL
# -----------------------------
@app.route("/export")
def export():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT a.user_id, u.name, a.team, a.date, a.status
        FROM attendance a
        LEFT JOIN users u ON a.user_id = u.user_id
    """)

    rows = c.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active

    headers = ["ID", "Name", "Team", "Date", "Status"]
    ws.append(headers)

    for row in rows:
        ws.append(row)

    align = Alignment(horizontal="center", vertical="center")
    border = Border(left=Side(style="thin"),
                    right=Side(style="thin"),
                    top=Side(style="thin"),
                    bottom=Side(style="thin"))

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = align
            cell.border = border

    file = io.BytesIO()
    wb.save(file)
    file.seek(0)

    return send_file(file,
        download_name="attendance.xlsx",
        as_attachment=True)

# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET","POST"])
def index():
    msg = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "checkin":
            msg = mark_attendance(request.form.get("user_id"))

        elif action == "add":
            msg = add_user(
                request.form.get("new_id"),
                request.form.get("name"),
                request.form.get("team"),
                request.form.get("shift"))

        elif action == "edit":
            msg = update_user(
                request.form.get("edit_id"),
                request.form.get("edit_name"),
                request.form.get("edit_team"),
                request.form.get("edit_shift"))

        elif action == "delete":
            msg = remove_user(request.form.get("edit_id"))

    data = get_dashboard()
    summary = get_summary(data)
    users = get_users()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width">
<style>
body{font-family:Arial;background:#f4f6f9;text-align:center}
.card{background:white;margin:15px;padding:15px;border-radius:10px}
input,select{padding:10px;margin:5px}
button{padding:10px;margin:5px}
a button{background:#0078D4;color:white;border:none}
</style>
</head>

<body>

<h2>📋 Attendance</h2>

<div class="card">
<form method="POST">
<input name="user_id" placeholder="ID">
<button name="action" value="checkin">Check In</button>
</form>
</div>

<div class="card">
<form method="POST">
<input name="new_id" placeholder="ID">
<input name="name" placeholder="Name">
<select name="team"><option>A</option><option>B</option><option>C</option></select>
<select name="shift"><option>Morning</option><option>Night</option></select>
<button name="action" value="add">Add User</button>
</form>
</div>

<div class="card">
<h3>📤 Export</h3>
/export
<button>⬇️ Download Excel</button>
</a>
</div>

<p>{{msg}}</p>

<h3>
✅ {{summary['1']}} |
⏱ {{summary['OT']}} |
❌ {{summary['NI']}} |
💤 {{summary['OFF']}}
</h3>

<div class="card">
<h3>User List</h3>
<table border="1" width="100%">
{% for u in users %}
<tr>
<form method="POST">
<td>{{u[0]}}</td>
<td><input name="edit_name" value="{{u[1]}}"></td>
<td>
<select name="edit_team">
<option {% if u[2]=='A' %}selected{% endif %}>A</option>
<option {% if u[2]=='B' %}selected{% endif %}>B</option>
<option {% if u[2]=='C' %}selected{% endif %}>C</option>
</select>
</td>
<td>
<select name="edit_shift">
<option {% if u[3]=='Morning' %}selected{% endif %}>Morning</option>
<option {% if u[3]=='Night' %}selected{% endif %}>Night</option>
</select>
</td>

<input type="hidden" name="edit_id" value="{{u[0]}}">

<td>
<button name="action" value="edit">Save</button>
<button name="action" value="delete">Delete</button>
</td>
</form>
</tr>
{% endfor %}
</table>
</div>

</body>
</html>
""", msg=msg, summary=summary, users=users)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
