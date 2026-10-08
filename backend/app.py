import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, g, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DB_PATH = BASE_DIR / "water_leaks.db"

VALID_SEVERITIES = ("low", "medium", "high", "critical")
VALID_STATUSES = ("submitted", "in_progress", "resolved","on_hold" "rejected")

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
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    area TEXT NOT NULL,
    severity TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
"""

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
        "2026-10-05 07:05:00",
    ),
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^(?:\+27|0)[1-9]\d{8}$")

app = Flask(__name__, static_folder=None)


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


def init_db():
    fresh = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    if fresh:
        conn.executemany(
            """
            INSERT INTO reports
                (full_name, email, phone, address, area, severity, description, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_REPORTS,
        )
    conn.commit()
    conn.close()


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


@app.get("/api/reports")
def list_reports():
    status = request.args.get("status", "").strip()
    area = request.args.get("area", "").strip()
    search = request.args.get("q", "").strip()

    sql = "SELECT * FROM reports WHERE 1=1"
    params = []

    if status:
        if status not in VALID_STATUSES:
            return jsonify(message="Validation failed.", errors={"status": "Invalid status value."}), 422
        sql += " AND status = ?"
        params.append(status)
    if area:
        sql += " AND area = ?"
        params.append(area)
    if search:
        sql += " AND (full_name LIKE ? OR address LIKE ? OR description LIKE ? OR area LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])

    sql += " ORDER BY datetime(created_at) DESC, id DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/reports")
def create_report():
    payload = request.get_json(silent=True) or {}
    data, errors = validate_report(payload)
    if errors:
        return jsonify(message="Validation failed.", errors=errors), 422

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO reports
            (full_name, email, phone, address, area, severity, description, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'submitted', ?)
        """,
        (
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
    row = db.execute("SELECT * FROM reports WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.get("/api/reports/<int:report_id>")
def get_report(report_id):
    row = get_db().execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        return jsonify(message="Report not found."), 404
    return jsonify(dict(row))


@app.put("/api/reports/<int:report_id>")
def update_report(report_id):
    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status") or "").strip().lower()
    if status not in VALID_STATUSES:
        return jsonify(message="Validation failed.", errors={"status": "Invalid status value."}), 422

    db = get_db()
    existing = db.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
    if existing is None:
        return jsonify(message="Report not found."), 404

    db.execute(
        "UPDATE reports SET status = ?, updated_at = ? WHERE id = ?",
        (status, now_utc(), report_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return jsonify(dict(row))


@app.delete("/api/reports/<int:report_id>")
def delete_report(report_id):
    db = get_db()
    existing = db.execute("SELECT id FROM reports WHERE id = ?", (report_id,)).fetchone()
    if existing is None:
        return jsonify(message="Report not found."), 404
    db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    db.commit()
    return jsonify(message=f"Report {report_id} deleted.", deleted_id=report_id)


@app.get("/api/stats")
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
        dict(row)
        for row in db.execute(
            "SELECT * FROM reports ORDER BY datetime(created_at) DESC, id DESC LIMIT 5"
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


@app.get("/js/<path:filename>")
def js_files(filename):
    return serve_frontend_file(f"js/{filename}")


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
