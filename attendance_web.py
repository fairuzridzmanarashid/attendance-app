from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)

DB_NAME = "attendance.db"

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT,
            time TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# INSERT ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    c.execute("INSERT INTO attendance (user_id, date, time) VALUES (?, ?, ?)",
              (uid, date, time))

    conn.commit()
    conn.close()

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    if request.method == "POST":
        uid = request.form.get("user_id")
        if uid:
            mark_attendance(uid)
            message = f"✅ Attendance recorded for ID {uid}"

    return render_template_string("""
    <html>
    <head>
        <title>Attendance System</title>
    </head>
    <body style="font-family:Arial; text-align:center; padding-top:50px;">

        <h1>📋 Attendance System</h1>

        <form method="POST">
            <input type="text" name="user_id" placeholder="Enter User ID" required>
            <br><br>
            <button type="submit">Submit</button>
        </form>

        <br>
        <p>{{message}}</p>

        <hr>

        <h2>📤 Export</h2>

        <!-- FIXED BUTTON -->
        /export
            <button style="
                padding:12px 20px;
                font-size:16px;
                background:#4CAF50;
                color:white;
                border:none;
                border-radius:6px;
                cursor:pointer;">
                ⬇ Download Excel
            </button>
        </a>

    </body>
    </html>
    """, message=message)

# -----------------------------
# EXPORT TO EXCEL
# -----------------------------
@app.route("/export")
def export_excel():
    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()

    file_path = "attendance_export.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
