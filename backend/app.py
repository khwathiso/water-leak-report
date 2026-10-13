import os
import re
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DB_PATH = BASE_DIR / "water_leaks.db"

VALID_SEVERITIES = ("low", "medium", "high", "critical")
VALID_STATUSES = ("submitted", "in_progress", "resolved", "on_hold", "rejected")
VALID_ROLES = ("citizen", "admin")

AREAS = [
    "Arcadia",
    "Atteridgeville",
    "Brooklyn",
    "Centurion",
    "Claremont",
    "Danville",
    "Garankuwa",
    "Hatfield",
    "Mamelodi",
    "Menlo Park",
    "muckleneuk",
    "Moreleta Park",
    "Pretoria Central",
    "Rietfontein",
    "Soshanguve",
    "Sunnyside",
    "Waverley",
    "Waterkloof",
    "Wonderboom",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    area TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""

# (username, email, password, role) - change these before any real use.
SEED_USERS = [
    ("admin", "admin@pretoria.gov.za", "admin123", "admin"),
    ("thabo", "thabo.mokoena@example.com", "password123", "citizen"),
    ("lerato", "lerato.nkosi@example.com", "password123", "citizen"),
]

# (full_name, email, phone, address, area, severity, description, status, owner_username, created_at)
SAMPLE_REPORTS = [
    (
        "Thabo Mokoena",
        "thabo.mokoena@example.com",
        "0821234567",
        "12 Stanza Bopape Street",
        "Pretoria Central",
        "critical",
        "Water main burst and the street outside the taxi rank is flooded.",
        "submitted",
        "thabo",
        "2026-10-01 08:15:00",
    ),
    (
        "Lerato Nkosi",
        "lerato.nkosi@example.com",
        "0739876543",
        "45 Duncan Street",
        "Hatfield",
        "medium",
        "Steady leak from the pavement joint near the university gate.",
        "in_progress",
        "lerato",
        "2026-10-03 11:40:00",
    ),
    (
        "Pieter van der Merwe",
        "pieter.vdm@example.com",
        "0845551234",
        "817 Sisulu Street",
        "Mamelodi",
        "high",
        "Burst pipe in the yard running water into the storm drain.",
        "resolved",
        None,
        "2026-10-05 07:05:00",
    ),
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(?:\+27|0)[1-9]\d{8}$")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")

# Configure static folder pointing to FRONTEND_DIR
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "pretoria-water-dev-secret-change-me")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def migrate(conn):
    columns = [row["name"] for row in conn.execute("PRAGMA table_info(reports)")]
    if "user_id" not in columns:
        conn.execute("ALTER TABLE reports ADD COLUMN user_id INTEGER")


def seed_users(conn):
    for username, email, password, role in SEED_USERS:
        conn.execute(
            """
            INSERT INTO users (username, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, email, generate_password_hash(password), role, now_utc()),
        )


def seed_reports(conn):
    for report in SAMPLE_REPORTS:
        owner = report[8]
        owner_id = None
        if owner:
            row = conn.execute("SELECT id FROM users WHERE username = ?", (owner,)).fetchone()
            owner_id = row["id"] if row else None
        conn.execute(
            """
            INSERT INTO reports
                (user_id, full_name, email, phone, address, area, severity, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                report[0],
                report[1],
                report[2],
                report[3],
                report[4],
                report[5],
                report[6],
                report[7],
                report[9],
            ),
        )


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    migrate(conn)
    if conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 0:
        seed_users(conn)
    if conn.execute("SELECT COUNT(*) AS count FROM reports").fetchone()["count"] == 0:
        seed_reports(conn)
    conn.commit()
    conn.close()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    row = get_db().execute(
        "SELECT id, username, email, role FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None:
        session.clear()
        return None
    return dict(row)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify(message="Authentication required. Please sign in."), 401
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def serialize_report(row):
    data = dict(row)
    user = g.get("user")
    if user is None:
        data["can_edit"] = False
    else:
        data["can_edit"] = user["role"] == "admin" or (
            data.get("user_id") is not None and data["user_id"] == user["id"]
        )
    return data


def validate_report(payload):
    errors = {}
    data = {}

    full_name = str(payload.get("full_name") or "").strip()
    if not full_name:
        errors["full_name"] = "Full name is required."
    elif len(full_name) < 2:
        errors["full_name"] = "Full name must be at least 2 characters."
    data["full_name"] = full_name

    email = str(payload.get("email") or "").strip().lower()
    if not email:
        errors["email"] = "Email address is required."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    data["email"] = email

    phone = re.sub(r"[\s\-()]", "", str(payload.get("phone") or ""))
    if not phone:
        errors["phone"] = "Phone number is required."
    elif not PHONE_RE.match(phone):
        errors["phone"] = "Enter a valid South African phone number, e.g. 0821234567."
    data["phone"] = phone

    address = str(payload.get("address") or "").strip()
    if not address:
        errors["address"] = "Street address is required."
    elif len(address) < 5:
        errors["address"] = "Street address must be at least 5 characters."
    data["address"] = address

    area = str(payload.get("area") or "").strip()
    if not area:
        errors["area"] = "Area is required."
    elif area not in AREAS:
        errors["area"] = "Select a valid Pretoria area."
    data["area"] = area

    severity = str(payload.get("severity") or "").strip().lower()
    if not severity:
        errors["severity"] = "Severity is required."
    elif severity not in VALID_SEVERITIES:
        errors["severity"] = "Severity must be low, medium, high or critical."
    data["severity"] = severity

    description = str(payload.get("description") or "").strip()
    if not description:
        errors["description"] = "Description is required."
    elif len(description) < 10:
        errors["description"] = "Description must be at least 10 characters."
    data["description"] = description

    return data, errors


def serve_frontend_file(filename):
    target = (FRONTEND_DIR / filename).resolve()
    try:
        target.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/areas")
def list_areas():
    return jsonify(AREAS)


@app.post("/api/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip().lower()
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")

    errors = {}
    if not username:
        errors["username"] = "Username is required."
    elif not USERNAME_RE.match(username):
        errors["username"] = "Username must be 3-20 characters (letters, numbers or underscore)."
    if not email:
        errors["email"] = "Email address is required."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if not password:
        errors["password"] = "Password is required."
    elif len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."
    if errors:
        return jsonify(message="Validation failed.", errors=errors), 422

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return jsonify(message="Validation failed.", errors={"username": "That username is already taken."}), 409
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify(message="Validation failed.", errors={"email": "That email is already registered."}), 409

    cursor = db.execute(
        "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, 'citizen', ?)",
        (username, email, generate_password_hash(password), now_utc()),
    )
    db.commit()
    session.clear()
    session["user_id"] = cursor.lastrowid
    user = db.execute(
        "SELECT id, username, email, role FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(dict(user)), 201


@app.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username") or "").strip().lower()
    password = str(payload.get("password") or "")

    if not username or not password:
        return jsonify(message="Username and password are required."), 422

    row = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return jsonify(message="Invalid username or password."), 401

    session.clear()
    session["user_id"] = row["id"]
    return jsonify(id=row["id"], username=row["username"], email=row["email"], role=row["role"])


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(message="Signed out.")


@app.get("/api/auth/me")
def me():
    user = current_user()
    if user is None:
        return jsonify(message="Not authenticated."), 401
    return jsonify(user)


@app.get("/api/reports")
@login_required
def list_reports():
    status = request.args.get("status", "").strip()
    area = request.args.get("area", "").strip()
    search = request.args.get("q", "").strip()

    sql = (
        "SELECT r.*, u.username AS reporter_username "
        "FROM reports r LEFT JOIN users u ON u.id = r.user_id WHERE 1=1"
    )
    params = []

    if status:
        if status not in VALID_STATUSES:
            return jsonify(message="Validation failed.", errors={"status": "Invalid status value."}), 422
        sql += " AND r.status = ?"
        params.append(status)
    if area:
        sql += " AND r.area = ?"
        params.append(area)
    if search:
        sql += " AND (r.full_name LIKE ? OR r.address LIKE ? OR r.description LIKE ? OR r.area LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])

    sql += " ORDER BY datetime(r.created_at) DESC, r.id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([serialize_report(row) for row in rows])


@app.post("/api/reports")
@login_required
def create_report():
    payload = request.get_json(silent=True) or {}
    data, errors = validate_report(payload)
    if errors:
        return jsonify(message="Validation failed.", errors=errors), 422

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO reports
            (user_id, full_name, email, phone, address, area, severity, description, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', ?)
        """,
        (
            g.user["id"],
            data["full_name"],
            data["email"],
            data["phone"],
            data["address"],
            data["area"],
            data["severity"],
            data["description"],
            now_utc(),
        ),
    )
    db.commit()
    row = db.execute(
        """
        SELECT r.*, u.username AS reporter_username
        FROM reports r LEFT JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return jsonify(serialize_report(row)), 201


@app.get("/api/reports/<int:report_id>")
@login_required
def get_report(report_id):
    row = get_db().execute(
        """
        SELECT r.*, u.username AS reporter_username
        FROM reports r LEFT JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
        """,
        (report_id,),
    ).fetchone()
    if row is None:
        return jsonify(message="Report not found."), 404
    return jsonify(serialize_report(row))


@app.put("/api/reports/<int:report_id>")
@login_required
def update_report(report_id):
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status") or "").strip().lower()
    if status not in VALID_STATUSES:
        return jsonify(message="Validation failed.", errors={"status": "Invalid status value."}), 422

    db = get_db()
    existing = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if existing is None:
        return jsonify(message="Report not found."), 404

    if g.user["role"] != "admin" and existing["user_id"] != g.user["id"]:
        return jsonify(message="You can only update reports that you created."), 403

    db.execute(
        "UPDATE reports SET status = ?, updated_at = ? WHERE id = ?",
        (status, now_utc(), report_id),
    )
    db.commit()
    row = db.execute(
        """
        SELECT r.*, u.username AS reporter_username
        FROM reports r LEFT JOIN users u ON u.id = r.user_id
        WHERE r.id = ?
        """,
        (report_id,),
    ).fetchone()
    return jsonify(serialize_report(row))


@app.delete("/api/reports/<int:report_id>")
@login_required
def delete_report(report_id):
    db = get_db()
    existing = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if existing is None:
        return jsonify(message="Report not found."), 404

    if g.user["role"] != "admin" and existing["user_id"] != g.user["id"]:
        return jsonify(message="You can only delete reports that you created."), 403

    db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    db.commit()
    return jsonify(message=f"Report {report_id} deleted.", deleted_id=report_id)


@app.get("/api/stats")
@login_required
def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) AS count FROM reports").fetchone()["count"]

    by_status = {status: 0 for status in VALID_STATUSES}
    for row in db.execute("SELECT status, COUNT(*) AS count FROM reports GROUP BY status"):
        by_status[row["status"]] = row["count"]

    by_severity = {severity: 0 for severity in VALID_SEVERITIES}
    for row in db.execute("SELECT severity, COUNT(*) AS count FROM reports GROUP BY severity"):
        by_severity[row["severity"]] = row["count"]

    by_area = [
        dict(area=row["area"], count=row["count"])
        for row in db.execute(
            "SELECT area, COUNT(*) AS count FROM reports GROUP BY area ORDER BY count DESC, area ASC"
        )
    ]

    critical_open = db.execute(
        """
        SELECT COUNT(*) AS count FROM reports
        WHERE severity = 'critical' AND status IN ('submitted', 'in_progress')
        """
    ).fetchone()["count"]

    recent = [
        serialize_report(row)
        for row in db.execute(
            """
            SELECT r.*, u.username AS reporter_username
            FROM reports r LEFT JOIN users u ON u.id = r.user_id
            ORDER BY datetime(r.created_at) DESC, r.id DESC LIMIT 5
            """
        )
    ]

    return jsonify(
        total=total,
        by_status=by_status,
        by_severity=by_severity,
        by_area=by_area,
        critical_open=critical_open,
        recent=recent,
        last_updated=now_utc(),
    )


@app.get("/")
def index_page():
    return serve_frontend_file("index.html")


@app.get("/index.html")
def index_html():
    return serve_frontend_file("index.html")


@app.get("/reports.html")
def reports_page():
    return serve_frontend_file("reports.html")


@app.get("/dashboard.html")
def dashboard_page():
    return serve_frontend_file("dashboard.html")


@app.get("/signin.html")
def signin_page():
    return serve_frontend_file("signin.html")


@app.get("/register.html")
def register_page():
    return serve_frontend_file("register.html")


@app.get("/js/<path:filename>")
def js_files(filename):
    return serve_frontend_file(f"js/{filename}")


# Initialize SQLite database on app load
init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
