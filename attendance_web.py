from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd
from io import BytesIO

app = Flask(__name__)
DB_NAME = "attendance.db"

# ✅ INIT DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT
        )
    """)

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

# ✅ DATE FORMAT UPDATED
def get_today():
    now = datetime.now()
    return now.strftime("%d/%m/%y"), now.strftime("%A")  # ✅ CHANGED FORMAT

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

# ✅ DASHBOARD DATA
def get_dashboard():
    today, _ = get_today()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, emp_id, date, status FROM attendance WHERE date=?", (today,))
    rows = c.fetchall()

    # counters
    present = sum(1 for r in rows if r[3] == "1")
    off = sum(1 for r in rows if r[3] == "OFF")

    c.execute("SELECT COUNT(*) FROM employees")
    total_users = c.fetchone()[0]

    not_marked = total_users - len(rows)

    conn.close()

    return rows, present, off, total_users, not_marked

# ✅ EXPORT EXCEL
@app.route("/export")
def export_excel():
    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query("""
        SELECT 
        name AS 'Name', 
        emp_id AS 'ID Badge', 
        date AS 'Date', 
        status AS 'Status' 
        FROM attendance
    """, conn)

    conn.close()

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')

        worksheet = writer.sheets['Attendance']
        for i, col in enumerate(df.columns):
            column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.column_dimensions[chr(65 + i)].width = column_width

    output.seek(0)

    return send_file(output, download_name="attendance.xlsx", as_attachment=True)

# ✅ UI
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

    data, present, off, total, not_marked = get_dashboard()

    html = """
    <style>
    body { font-family: Arial; background:#f4f6f8; }
    .container { max-width:1000px; margin:auto; }

    .card {
        background:white; padding:20px; margin:15px 0;
        border-radius:10px; box-shadow:0 2px 6px rgba(0,0,0,0.1);
    }

    input, select, button {
        width:100%; padding:14px; margin:5px 0;
        border-radius:8px; font-size:18px;
    }

