from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd
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
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            name TEXT,
            id TEXT PRIMARY KEY,
            team TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id TEXT,
            date TEXT,
            day TEXT,
            status TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# GET TODAY
# -----------------------------
def get_today():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%A")

# -----------------------------
# AUTO MARK (NI / OFF)
# -----------------------------
def auto_mark_status():
    today, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT id, team FROM users")
    users = c.fetchall()

    for uid, team in users:
        c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, today))
        exists = c.fetchone()

        if not exists:
            # ✅ CORRECT SYNTAX (THIS IS THE FIX)
            if today_day in TEAM_SCHEDULE[team] = "NI"   # working day but not scanned
            else:
                status = "OFF"  # not working day

            c.execute(
                "INSERT INTO attendance VALUES (?, ?, ?, ?)",
                (uid, today, today_day, status)
            )

    conn.commit()
    conn.close()

# -----------------------------
# ADD USER
# -----------------------------
def add_user(name, uid, team):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (name, uid, team))
        conn.commit()
        msg = "✅ User added"
    except sqlite3.IntegrityError:
        msg = "❌ Duplicate ID not allowed"

    conn.close()
    return msg

# -----------------------------
# REMOVE USER
# -----------------------------
def remove_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return "🗑️ User removed"

# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    today, today_day = get_today()

    c.execute("SELECT team FROM users WHERE id=?", (uid,))
    user = c.fetchone()

    if not user:
        conn.close()
        return "❌ User not found"

    team = user[0]

    # ✅ CORRECT SYNTAX
    if today_day in TEAM_SCHEDULEnew_status = "1"
    else:
        new_status = "OT"

    # Check existing record
    c.execute("SELECT status FROM attendance WHERE id=? AND date=?", (uid, today))
    existing = c.fetchone()

    if existing:
        c.execute("""
            UPDATE attendance
            SET status=?
            WHERE id=? AND date=?
        """, (new_status, uid, today))
    else:
        c.execute(
            "INSERT INTO attendance VALUES (?, ?, ?, ?)",
            (uid, today, today_day, new_status)
        )

    conn.commit()
    conn.close()

    return f"✅ Recorded as {new_status}"

# -----------------------------
# EXPORT USERS TO EXCEL
# -----------------------------
def export_excel():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT name, id, team FROM users", conn)
    conn.close()

    df.columns = ["Name", "ID Badge", "Team"]

    file_path = "users.xlsx"

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Users")
        ws = writer.sheets["Users"]

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter

            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))

            ws.column_dimensions[col_letter].width = max_len + 2

    return file_path

# -----------------------------
# GET USERS
# -----------------------------
def get_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT name, id, team FROM users")
    data = c.fetchall()
    conn.close()
    return data

# -----------------------------
# SUMMARY
# -----------------------------
def get_summary():
    today, _ = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT status, COUNT(*) 
        FROM attendance 
        WHERE date=? 
        GROUP BY status
    """, (today,))

    rows = c.fetchall()
    conn.close()

    summary = {"1": 0, "OT": 0, "OFF": 0, "NI": 0}

    for status, count in rows:
        summary[status] = count

    return summary

# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():

    auto_mark_status()

    message = ""
    today, day = get_today()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            message = add_user(
                request.form["name"],
                request.form["id"],
                request.form["team"]
            )

        elif action == "remove":
            message = remove_user(request.form["id"])

        elif action == "mark":
            message = mark_attendance(request.form["id"])

        elif action == "export":
            return send_file(export_excel(), as_attachment=True)

    users = get_users()
    summary = get_summary()

    html = """
    <h2>📊 Attendance System</h2>
    <h4>{{today}} ({{day}})</h4>

    <p>✅ Present: {{summary['1']}}</p>
    <p>🟧 OT: {{summary['OT']}}</p>
    <p>⬜ OFF: {{summary['OFF']}}</p>
    <p>🟥 NI: {{summary['NI']}}</p>

    <hr>

    <form method="POST">
        <input name="name" placeholder="Name" required>
        <input name="id" placeholder="ID Badge" required>
        <input name="team" placeholder="Team (A/B/C)" required>
        <button name="action" value="add">Add User</button>
    </form>

    <form method="POST">
        <input name="id" placeholder="ID Badge">
        <button name="action" value="remove">Remove User</button>
    </form>

    <form method="POST">
        <input name="id" placeholder="Scan ID">
        <button name="action" value="mark">Scan</button>
    </form>

    <form method="POST">
        <button name="action" value="export">Export Excel</button>
    </form>

    <h3>Users</h3>
    <ul>
    {% for u in users %}
        <li>{{u[0]}} | {{u[1]}} | Team {{u[2]}}</li>
    {% endfor %}
    </ul>

    <p>{{message}}</p>
    """

    return render_template_string(
        html,
        today=today,
        day=day,
        users=users,
        summary=summary,
        message=message
    )

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
