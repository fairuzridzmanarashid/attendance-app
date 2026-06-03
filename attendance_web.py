from flask import Flask, request, render_template_string, send_file, redirect
import sqlite3
from datetime import datetime
import os
import pandas as pd

app = Flask(__name__)

DB_NAME = "attendance.db"

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

    # attendance table
    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT
        )
    """)

    # users table ✅ NEW
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# DATE FORMAT ✅ dd/mm/yy
# -----------------------------
def get_today():
    now = datetime.now()
    return now.strftime("%d/%m/%y"), now.strftime("%A")

# -----------------------------
# USER FUNCTIONS ✅ NEW
# -----------------------------
def get_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, team FROM users")
    users = [{"id": r[0], "name": r[1], "team": r[2]} for r in c.fetchall()]
    conn.close()
    return users

def add_user(uid, name, team):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (uid, name, team))
        conn.commit()
    except:
        pass
    conn.close()

def delete_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()

def find_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, name, team FROM users WHERE id=?", (uid,))
    row = c.fetchone()
    conn.close()
    return {"id": row[0], "name": row[1], "team": row[2]} if row else None

# -----------------------------
# ATTENDANCE
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
# DASHBOARD ✅ OT / NI LOGIC
# -----------------------------
def get_dashboard():
    today, today_day = get_today()
    users = get_users()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    result = []

    for u in users:
        uid = u["id"]
        team = u["team"]

        working = today_day in TEAM_SCHEDULE.get(team, [])

        c.execute("SELECT 1 FROM attendance WHERE user_id=? AND date=?", (uid, today))
        scanned = c.fetchone() is not None

        if working and scanned:
            status = "1"
        elif not working and scanned:
            status = "OT"
        elif working and not scanned:
            status = "NI"
        else:
            status = "OFF"

        result.append({
            "id": uid,
            "name": u["name"],
            "team": team,
            "date": today,
            "day": today_day,
            "status": status
        })

    conn.close()
    return result

# -----------------------------
# EXPORT ✅ GUARANTEED WORKING
# -----------------------------
@app.route("/export")
def export_excel():
    data = get_dashboard()
    df = pd.DataFrame(data)

    filename = f"attendance_{datetime.now().strftime('%d%m%y')}.xlsx"
    filepath = os.path.join(os.getcwd(), filename)

    df.to_excel(filepath, index=False)

    return send_file(filepath,
                     as_attachment=True,
                     download_name=filename)

# -----------------------------
# MAIN PAGE
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        action = request.form.get("action")

        if action == "scan":
            uid = request.form.get("uid")
            if find_user(uid):
                message = mark_attendance(uid)
            else:
                message = "User not found"

        elif action == "add":
            add_user(
                request.form.get("new_id"),
                request.form.get("name"),
                request.form.get("team")
            )
            return redirect("/")

        elif action == "delete":
            delete_user(request.form.get("del_id"))
            return redirect("/")

    data = get_dashboard()
    today, today_day = get_today()

    return render_template_string("""
    <html>
    <head>
    <style>
    body { font-family: Arial; background:#f2f2f2; text-align:center; }
    .box { background:white; padding:20px; margin:20px auto; width:85%; border-radius:10px; }
    table { width:100%; border-collapse:collapse; }
    th, td { padding:10px; border:1px solid #ddd; }
    th { background:#007BFF; color:white; }
    .btn { padding:10px 20px; background:#007BFF; color:white; border:none; border-radius:6px; cursor:pointer; }
    </style>
    </head>

    <body>

    <div class="box">
        <h2>Attendance System</h2>
        <h4>{{today}} ({{today_day}})</h4>

        <h3>Scan</h3>
        <form method="POST">
            <input name="uid" placeholder="Scan ID">
            <button class="btn" name="action" value="scan">Submit</button>
        </form>

        <p>{{message}}</p>

        <h3>Add User</h3>
        <form method="POST">
            <input name="new_id" placeholder="ID" required>
            <input name="name" placeholder="Name" required>
            <input name="team" placeholder="Team (A/B/C)" required>
            <button class="btn" name="action" value="add">Add</button>
        </form>

        <h3>Remove User</h3>
        <form method="POST">
            <input name="del_id" placeholder="ID">
            <button class="btn" name="action" value="delete">Delete</button>
        </form>

        <h3>Dashboard</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Team</th>
                <th>Date</th>
                <th>Day</th>
                <th>Status</th>
            </tr>

            {% for r in data %}
            <tr>
                <td>{{r.id}}</td>
                <td>{{r.name}}</td>
                <td>{{r.team}}</td>
                <td>{{r.date}}</td>
                <td>{{r.day}}</td>
                <td><b>{{r.status}}</b></td>
            </tr>
            {% endfor %}
        </table>

        <br>

        <!-- ✅ REAL WORKING BUTTON -->
        /export
            <button class="btn">⬇ Export Excel</button>
        </form>

    </div>
    </body>
    </html>
    """, data=data, message=message, today=today, today_day=today_day)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
