from flask import Flask, request, render_template_string, send_file
import sqlite3
from datetime import datetime
import pandas as pd

app = Flask(__name__)

DB_NAME = "attendance.db"

# -----------------------------
# SHIFT SCHEDULE
# -----------------------------
TEAM_SCHEDULE = {
    "Day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "Night": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]
}

# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            shift TEXT,
            team TEXT
        )
    """)

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


def format_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%a')} {dt.day}/{dt.month}"


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
def add_user(name, uid, shift, team):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (uid, name, shift, team))
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
# AUTO OFF / NI
# -----------------------------
def auto_mark_absent(selected_date):
    dt = datetime.strptime(selected_date, "%Y-%m-%d")
    today_day = dt.strftime("%A")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    for u in users:
        uid = u[0]
        shift = u[2]

        c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, selected_date))
        record = c.fetchone()

        if not record:
            working_days = TEAM_SCHEDULE[shift]

            if today_day in working_days:
                status = "NI"
            else:
                status = "OFF"

            c.execute(
                "INSERT INTO attendance VALUES (?, ?, ?)",
                (uid, selected_date, status)
            )

    conn.commit()
    conn.close()


# -----------------------------
# MARK ATTENDANCE
# -----------------------------
def mark_attendance(uid):
    user = get_user(uid)

    if not user:
        return "❌ User not found"

    today_date, today_day = get_today()
    shift = user[2]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM attendance WHERE id=? AND date=?", (uid, today_date))
    record = c.fetchone()

    working_days = TEAM_SCHEDULE[shift]

    if record:
        if record[2] == "OFF":
            c.execute("UPDATE attendance SET status='OT' WHERE id=? AND date=?", (uid, today_date))
            conn.commit()
            conn.close()
            return f"🔥 OT recorded: {user[1]}"

        elif record[2] == "NI":
            c.execute("UPDATE attendance SET status='1' WHERE id=? AND date=?", (uid, today_date))
            conn.commit()
            conn.close()
            return f"✅ Present: {user[1]}"

        else:
            conn.close()
            return "⚠️ Already recorded"

    if today_day in working_days:
        status = "1"
    else:
        status = "OT"

    c.execute("INSERT INTO attendance VALUES (?, ?, ?)", (uid, today_date, status))
    conn.commit()
    conn.close()

    return f"✅ Recorded: {user[1]}"


# -----------------------------
# EXPORT EXCEL
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
# DASHBOARD UI
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    message = ""

    selected_date = request.form.get("date")

    if not selected_date:
        selected_date, _ = get_today()

    auto_mark_absent(selected_date)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            message = add_user(
                request.form.get("name"),
                request.form.get("uid"),
                request.form.get("shift"),
                request.form.get("team")
            )

        elif action == "remove":
            message = remove_user(request.form.get("uid"))

        elif action == "attendance":
            message = mark_attendance(request.form.get("uid"))

        elif action == "export":
            file = export_excel()
            return send_file(file, as_attachment=True)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT u.id, u.name, u.shift, u.team, a.status
        FROM users u
        LEFT JOIN attendance a
        ON u.id = a.id AND a.date = ?
    """, (selected_date,))

    data = c.fetchall()

    summary = {"1": 0, "OT": 0, "OFF": 0, "NI": 0}

    for d in data:
        status = d[4] if d[4] else "NI"
        if status in summary:
            summary[status] += 1

    conn.close()

    display_date = format_date(selected_date)

    return render_template_string("""
<html>
<head>
<style>
body { font-family: Arial; margin: 20px; }

.grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

.card {
    padding: 20px;
    text-align: center;
    color: white;
    border-radius: 10px;
}

.present { background: green; }
.ot { background: orange; }
.off { background: gray; }
.ni { background: red; }

.section {
    border: 1px solid #ccc;
    padding: 15px;
    margin-top: 20px;
    border-radius: 10px;
}

input, select, button {
    padding: 10px;
    margin: 5px;
}

table {
    width: 100%;
    margin-top: 20px;
    border-collapse: collapse;
}

th, td {
    padding: 10px;
    border-bottom: 1px solid #ddd;
}
</style>
</head>

<body>

<h2>📊 Attendance Dashboard ({{display_date}})</h2>

<div class="section">
    <form method="post">
        <input type="date" name="date" value="{{selected_date}}">
        <button type="submit">View</button>
    </form>
</div>

<div class="grid">
    <div class="card present">Present<br>{{summary['1']}}</div>
    <div class="card ot">OT<br>{{summary['OT']}}</div>
    <div class="card off">OFF<br>{{summary['OFF']}}</div>
    <div class="card ni">NI<br>{{summary['NI']}}</div>
</div>

<div class="section">
    <h3>Scan Attendance</h3>
    <form method="post">
        <input name="uid" placeholder="ID">
        <button name="action" value="attendance">Submit</button>
    </form>
</div>

<div class="section">
    <h3>Add User</h3>
    <form method="post">
        <input name="name" placeholder="Name">
        <input name="uid" placeholder="ID">
        <select name="shift">
            <option>Day</option>
            <option>Night</option>
        </select>
        <select name="team">
            <option>A</option>
            <option>B</option>
            <option>C</option>
        </select>
        <button name="action" value="add">Add</button>
    </form>
</div>

<div class="section">
    <h3>Remove User</h3>
    <form method="post">
        <input name="uid" placeholder="ID">
        <button name="action" value="remove">Remove</button>
    </form>
</div>

<div class="section">
    <form method="post">
        <button name="action" value="export">Download Excel</button>
    </form>
</div>

<table>
<tr>
<th>ID</th><th>Name</th><th>Shift</th><th>Team</th><th>Status</th>
</tr>

{% for u in data %}
<tr>
<td>{{u[0]}}</td>
<td>{{u[1]}}</td>
<td>{{u[2]}}</td>
<td>{{u[3]}}</td>
<td>
{% if u[4] == '1' %}
<span style="color:green">Present</span>
{% elif u[4] == 'OT' %}
<span style="color:orange">OT</span>
{% elif u[4] == 'OFF' %}
<span style="color:gray">OFF</span>
{% else %}
<span style="color:red">NI</span>
{% endif %}
</td>
</tr>
{% endfor %}
</table>

<h3>{{message}}</h3>

</body>
</html>
""", data=data, summary=summary, message=message,
       selected_date=selected_date, display_date=display_date)


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
