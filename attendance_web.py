from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import os
import pandas as pd

app = Flask(__name__)

DB_NAME = "attendance.db"

# -----------------------------
# SHIFT SCHEDULE (KEY LOGIC)
# -----------------------------
TEAM_SCHEDULE = {
    "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Night": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
}

# -----------------------------
# DATABASE INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # USERS
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            shift TEXT
        )
    """)

    # ATTENDANCE
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


def get_user(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (uid,))
    user = c.fetchone()
    conn.close()
    return user


# -----------------------------
# ADD USER
# -----------------------------
def add_user(name, uid, shift):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (uid, name, shift))
        conn.commit()
        msg = "✅ User added"
    except:
        msg = "❌ User already exists"

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

    return "🗑 User removed"


# -----------------------------
# AUTO OFF / NI (IMPORTANT)
# -----------------------------
def auto_mark_absent():
    today_date, today_day = get_today()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    for u in users:
        uid = u[0]
        shift = u[2]

        # check if already has record
        c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, today_date))
        record = c.fetchone()

        if not record:
            working_days = TEAM_SCHEDULE[shift]

            if today_day in working_days:
                status = "NI"   # Not In
            else:
                status = "OFF"  # Off Day

            c.execute(
                "INSERT INTO attendance VALUES (?, ?, ?)",
                (uid, today_date, status)
            )

    conn.commit()
    conn.close()


# -----------------------------
# MARK ATTENDANCE (MAIN LOGIC)
# -----------------------------
def mark_attendance(uid):
    user = get_user(uid)

    if not user:
        return "❌ User not found"

    today_date, today_day = get_today()
    shift = user[2]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # check existing record
    c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, today_date))
    record = c.fetchone()

    working_days = TEAM_SCHEDULE[shift]

    if record:
        # ✅ If previously OFF → convert to OT
        if record[2] == "OFF":
            c.execute("""
                UPDATE attendance
                SET status='OT'
                WHERE id=? AND date=?
            """, (uid, today_date))
            conn.commit()
            conn.close()
            return f"🔥 OT recorded (worked on OFF day): {user[1]}"

        # ✅ If previously NI → convert to normal
        elif record[2] == "NI":
            c.execute("""
                UPDATE attendance
                SET status='1'
                WHERE id=? AND date=?
            """, (uid, today_date))
            conn.commit()
            conn.close()
            return f"✅ Attendance recorded: {user[1]}"

        else:
            conn.close()
            return "⚠️ Already marked today"

    # if no record (rare)
    if today_day in working_days:
        status = "1"
    else:
        status = "OT"

    c.execute(
        "INSERT INTO attendance VALUES (?, ?, ?)",
        (uid, today_date, status)
    )

    conn.commit()
    conn.close()

    return f"✅ Attendance recorded: {user[1]}"


# -----------------------------
# EXPORT TO EXCEL
# -----------------------------
def export_excel():
    conn = sqlite3.connect(DB_NAME)

    users_df = pd.read_sql_query("SELECT * FROM users", conn)
    att_df = pd.read_sql_query("SELECT * FROM attendance", conn)

    file_name = "attendance_export.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        users_df.to_excel(writer, sheet_name="Users", index=False)
        att_df.to_excel(writer, sheet_name="Attendance", index=False)

    conn.close()
    return file_name


# -----------------------------
# WEB UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    # ✅ IMPORTANT: Run daily auto marking
    auto_mark_absent()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            message = add_user(
                request.form.get("name"),
                request.form.get("uid"),
                request.form.get("shift")
            )

        elif action == "remove":
            message = remove_user(request.form.get("uid"))

        elif action == "attendance":
            message = mark_attendance(request.form.get("uid"))

        elif action == "export":
            file = export_excel()
            return send_file(file, as_attachment=True)

    return render_template_string("""
    <h2>Attendance System</h2>

    <h3>Add User</h3>
    <form method="post">
        Name: <input name="name"><br>
        Badge ID: <input name="uid"><br>
        Shift:
        <select name="shift">
            <option>Day</option>
            <option>Night</option>
        </select><br>
        <button name="action" value="add">Add User</button>
    </form>

    <h3>Remove User</h3>
    <form method="post">
        Badge ID: <input name="uid">
        <button name="action" value="remove">Remove</button>
    </form>

    <h3>Mark Attendance</h3>
    <form method="post">
        Badge ID: <input name="uid">
        <button name="action" value="attendance">Scan</button>
    </form>

    <h3>Export</h3>
    <form method="post">
        <button name="action" value="export">Download Excel</button>
    </form>

    <p><b>{{message}}</b></p>
    """ , message=message)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
