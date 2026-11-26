"""
Campus Connect - Integrated Student Enrollment and Information System
=====================================================================
Flask + SQLite REST API backend.

This one service combines two laboratory activities:

  * Laboratory 3 - Student Course Management API
        /api/courses  (course_id, course_code, course_name, department)

  * Laboratory 4 - Campus Connect Student Information Portal
        /api/students, /api/enrollments, /api/announcements

  * Integration layer - shared dashboard statistics
        /api/stats, /api/health

The SQLite database file (database.db) is created and filled with fictional
sample records automatically the first time the application starts.

Run locally:
    python app.py
    then open http://127.0.0.1:5000

Author: Campus Connect Laboratory Project (fictional data only)
"""

import os
import secrets
import sqlite3
from datetime import datetime

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "database.db")
COURSE_CAPACITY = int(os.environ.get("COURSE_CAPACITY", "30"))
ALLOWED_STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")

app = Flask(__name__)

# The React frontend and the HTML pages both call this API from another origin,
# so cross-origin requests must be allowed. Set CORS_ORIGINS to a comma separated
# list in production if you want to restrict it.
_origins = os.environ.get("CORS_ORIGINS", "*")
if _origins != "*":
    _origins = [item.strip() for item in _origins.split(",") if item.strip()]
CORS(app, resources={r"/api/*": {"origins": _origins}})


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """One SQLite connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_all(sql, args=()):
    return [dict(row) for row in get_db().execute(sql, args).fetchall()]


def query_one(sql, args=()):
    row = get_db().execute(sql, args).fetchone()
    return dict(row) if row else None


def now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def fail(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Schema + sample data
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'staff',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL UNIQUE,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    program        TEXT NOT NULL,
    year_level     TEXT NOT NULL,
    contact_number TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    department  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,
    course_id       INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Pending',
    UNIQUE (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS announcements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    date_posted TEXT NOT NULL,
    author      TEXT NOT NULL DEFAULT 'Registrar''s Office'
);
"""

SAMPLE_STUDENTS = [
    ("2024-00101", "Maria Clara", "Dela Cruz", "maria.delacruz@campusconnect.edu.ph",
     "BS Information Technology", "2nd Year", "0917-555-0101"),
    ("2024-00102", "Juan Miguel", "Santos", "juan.santos@campusconnect.edu.ph",
     "BS Computer Science", "3rd Year", "0917-555-0102"),
    ("2024-00103", "Ana Sofia", "Reyes", "ana.reyes@campusconnect.edu.ph",
     "BS Accountancy", "1st Year", "0917-555-0103"),
    ("2024-00104", "Paolo Gabriel", "Mendoza", "paolo.mendoza@campusconnect.edu.ph",
     "BS Civil Engineering", "4th Year", "0917-555-0104"),
    ("2024-00105", "Liza Marie", "Bautista", "liza.bautista@campusconnect.edu.ph",
     "BS Nursing", "2nd Year", "0917-555-0105"),
    ("2024-00106", "Mark Anthony", "Villanueva", "mark.villanueva@campusconnect.edu.ph",
     "BS Information Technology", "3rd Year", "0917-555-0106"),
]

SAMPLE_COURSES = [
    ("CS101", "Introduction to Computing", "College of Computing Studies"),
    ("IT201", "Web Systems and Technologies", "College of Computing Studies"),
    ("CS205", "Data Structures and Algorithms", "College of Computing Studies"),
    ("ACC110", "Principles of Accounting", "College of Business"),
    ("CE210", "Structural Analysis", "College of Engineering"),
    ("NUR120", "Fundamentals of Nursing", "College of Nursing"),
]

SAMPLE_ENROLLMENTS = [
    (1, 1, "Approved"),
    (1, 2, "Pending"),
    (2, 2, "Approved"),
    (2, 3, "Pending"),
    (3, 4, "Approved"),
    (4, 5, "Rejected"),
    (5, 6, "Approved"),
]

SAMPLE_ANNOUNCEMENTS = [
    ("Enrollment period for the first semester",
     "Online enrollment for the first semester of academic year 2026-2027 opens on June 3 and closes on June 21. Submit your course requests through the Campus Connect enrollment module.",
     "Registrar's Office"),
    ("Scholarship applications now open",
     "The Office of Student Affairs is accepting scholarship applications until the end of the month. Requirements: certificate of enrollment, latest grades, and a one page essay.",
     "Office of Student Affairs"),
    ("Laboratory schedule adjustment",
     "All computing laboratory classes will shift to the new laboratory rooms starting next week. Check your course page for the updated room assignment.",
     "College of Computing Studies"),
]


def init_db():
    """Creates the tables and seeds fictional sample data if the database is empty."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)

    def count(table):
        return connection.execute("SELECT COUNT(*) AS total FROM " + table).fetchone()["total"]

    if count("students") == 0:
        connection.executemany(
            "INSERT INTO students (student_id, first_name, last_name, email, program,"
            " year_level, contact_number, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [row + (now_iso(),) for row in SAMPLE_STUDENTS],
        )
    if count("courses") == 0:
        connection.executemany(
            "INSERT INTO courses (course_code, course_name, department) VALUES (?, ?, ?)",
            SAMPLE_COURSES,
        )
    if count("enrollments") == 0:
        connection.executemany(
            "INSERT INTO enrollments (student_id, course_id, enrollment_date, status)"
            " VALUES (?, ?, ?, ?)",
            [(student, course, today(), status) for student, course, status in SAMPLE_ENROLLMENTS],
        )
    if count("announcements") == 0:
        connection.executemany(
            "INSERT INTO announcements (title, content, date_posted, author)"
            " VALUES (?, ?, ?, ?)",
            [(title, content, now_iso(), author) for title, content, author in SAMPLE_ANNOUNCEMENTS],
        )
    if count("users") == 0:
        # The users table is part of the required schema. No plaintext password is
        # ever stored or committed: a random unusable hash is generated at first run.
        connection.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                "registrar",
                "registrar@campusconnect.edu.ph",
                generate_password_hash(secrets.token_hex(24)),
                "admin",
                now_iso(),
            ),
        )

    connection.commit()
    connection.close()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_student(data, student_pk=None):
    cleaned = {}
    errors = {}
    required = [
        ("student_id", "Student ID"),
        ("first_name", "First name"),
        ("last_name", "Last name"),
        ("email", "Email"),
        ("program", "Program"),
        ("year_level", "Year level"),
    ]
    for field, label in required:
        value = str(data.get(field) or "").strip()
        cleaned[field] = value
        if not value:
            errors[field] = label + " is required."

    cleaned["contact_number"] = str(data.get("contact_number") or "").strip()

    if cleaned["email"] and "@" not in cleaned["email"]:
        errors["email"] = "Enter a valid email address."

    if cleaned["student_id"]:
        existing = query_one("SELECT id FROM students WHERE student_id = ?", (cleaned["student_id"],))
        if existing and existing["id"] != student_pk:
            errors["student_id"] = "That student ID is already registered."
    if cleaned["email"]:
        existing = query_one("SELECT id FROM students WHERE email = ?", (cleaned["email"],))
        if existing and existing["id"] != student_pk:
            errors["email"] = "That email is already used by another student."

    return cleaned, errors


def validate_course(data, course_pk=None):
    cleaned = {
        "course_code": str(data.get("course_code") or "").strip().upper(),
        "course_name": str(data.get("course_name") or "").strip(),
        "department": str(data.get("department") or "").strip(),
    }
    errors = {}
    for field, label in [
        ("course_code", "Course code"),
        ("course_name", "Course name"),
        ("department", "Department"),
    ]:
        if not cleaned[field]:
            errors[field] = label + " is required."

    if cleaned["course_code"]:
        existing = query_one(
            "SELECT course_id FROM courses WHERE course_code = ?", (cleaned["course_code"],)
        )
        if existing and existing["course_id"] != course_pk:
            errors["course_code"] = "That course code already exists."

    return cleaned, errors


def validate_announcement(data):
    cleaned = {
        "title": str(data.get("title") or "").strip(),
        "content": str(data.get("content") or "").strip(),
        "author": str(data.get("author") or "").strip() or "Registrar's Office",
    }
    errors = {}
    if not cleaned["title"]:
        errors["title"] = "Title is required."
    if not cleaned["content"]:
        errors["content"] = "Content is required."
    return cleaned, errors


# ---------------------------------------------------------------------------
# Health + statistics (integration layer)
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "Campus Connect API",
            "version": "1.0.0",
            "database": os.path.basename(DATABASE_PATH),
            "time": now_iso(),
        }
    )


@app.get("/api/stats")
def stats():
    total_students = query_one("SELECT COUNT(*) AS total FROM students")["total"]
    total_courses = query_one("SELECT COUNT(*) AS total FROM courses")["total"]
    total_enrollments = query_one("SELECT COUNT(*) AS total FROM enrollments")["total"]
    pending = query_one(
        "SELECT COUNT(*) AS total FROM enrollments WHERE status = 'Pending'"
    )["total"]
    approved = query_one(
        "SELECT COUNT(*) AS total FROM enrollments WHERE status = 'Approved'"
    )["total"]
    full_courses = query_one(
        "SELECT COUNT(*) AS total FROM ("
        "  SELECT c.course_id FROM courses c"
        "  LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'Approved'"
        "  GROUP BY c.course_id HAVING COUNT(e.enrollment_id) >= ?"
        ")",
        (COURSE_CAPACITY,),
    )["total"]

    return jsonify(
        {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_enrollments": total_enrollments,
            "available_courses": max(total_courses - full_courses, 0),
            "pending_enrollments": pending,
            "approved_enrollments": approved,
            "course_capacity": COURSE_CAPACITY,
        }
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@app.get("/api/students")
def list_students():
    search = (request.args.get("search") or "").strip()
    sql = "SELECT * FROM students"
    args = []
    if search:
        like = "%" + search + "%"
        sql += (
            " WHERE student_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
            " OR email LIKE ? OR program LIKE ?"
        )
        args = [like, like, like, like, like]
    sql += " ORDER BY last_name ASC, first_name ASC"
    return jsonify(query_all(sql, args))


@app.get("/api/students/<int:student_pk>")
def get_student(student_pk):
    student = query_one("SELECT * FROM students WHERE id = ?", (student_pk,))
    if not student:
        return fail("Student not found.", 404)
    return jsonify(student)


@app.post("/api/students")
def create_student():
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_student(data)
    if errors:
        return jsonify({"error": "Please check the student details.", "fields": errors}), 400

    cursor = get_db().execute(
        "INSERT INTO students (student_id, first_name, last_name, email, program,"
        " year_level, contact_number, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            cleaned["student_id"],
            cleaned["first_name"],
            cleaned["last_name"],
            cleaned["email"],
            cleaned["program"],
            cleaned["year_level"],
            cleaned["contact_number"],
            now_iso(),
        ),
    )
    get_db().commit()
    created = query_one("SELECT * FROM students WHERE id = ?", (cursor.lastrowid,))
    return jsonify(created), 201


@app.put("/api/students/<int:student_pk>")
def update_student(student_pk):
    if not query_one("SELECT id FROM students WHERE id = ?", (student_pk,)):
        return fail("Student not found.", 404)

    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_student(data, student_pk)
    if errors:
        return jsonify({"error": "Please check the student details.", "fields": errors}), 400

    get_db().execute(
        "UPDATE students SET student_id = ?, first_name = ?, last_name = ?, email = ?,"
        " program = ?, year_level = ?, contact_number = ? WHERE id = ?",
        (
            cleaned["student_id"],
            cleaned["first_name"],
            cleaned["last_name"],
            cleaned["email"],
            cleaned["program"],
            cleaned["year_level"],
            cleaned["contact_number"],
            student_pk,
        ),
    )
    get_db().commit()
    return jsonify(query_one("SELECT * FROM students WHERE id = ?", (student_pk,)))


@app.delete("/api/students/<int:student_pk>")
def delete_student(student_pk):
    if not query_one("SELECT id FROM students WHERE id = ?", (student_pk,)):
        return fail("Student not found.", 404)
    get_db().execute("DELETE FROM students WHERE id = ?", (student_pk,))
    get_db().commit()
    return jsonify({"message": "Student deleted.", "id": student_pk})


@app.get("/api/students/<int:student_pk>/enrollments")
def student_enrollments(student_pk):
    if not query_one("SELECT id FROM students WHERE id = ?", (student_pk,)):
        return fail("Student not found.", 404)
    return jsonify(enrollment_query(where="WHERE e.student_id = ?", args=[student_pk]))


# ---------------------------------------------------------------------------
# Courses (Laboratory 3 contract preserved)
# ---------------------------------------------------------------------------
def course_query(search=None):
    sql = (
        "SELECT c.course_id, c.course_code, c.course_name, c.department,"
        " (SELECT COUNT(*) FROM enrollments e"
        "   WHERE e.course_id = c.course_id AND e.status = 'Approved') AS enrolled_count"
        " FROM courses c"
    )
    args = []
    if search:
        like = "%" + search + "%"
        sql += " WHERE c.course_code LIKE ? OR c.course_name LIKE ? OR c.department LIKE ?"
        args = [like, like, like]
    sql += " ORDER BY c.course_code ASC"
    rows = query_all(sql, args)
    for row in rows:
        row["slots_left"] = max(COURSE_CAPACITY - int(row["enrolled_count"] or 0), 0)
    return rows


@app.get("/api/courses")
def list_courses():
    return jsonify(course_query((request.args.get("search") or "").strip() or None))


@app.get("/api/courses/<int:course_pk>")
def get_course(course_pk):
    row = query_one(
        "SELECT c.course_id, c.course_code, c.course_name, c.department,"
        " (SELECT COUNT(*) FROM enrollments e"
        "   WHERE e.course_id = c.course_id AND e.status = 'Approved') AS enrolled_count"
        " FROM courses c WHERE c.course_id = ?",
        (course_pk,),
    )
    if not row:
        return fail("Course not found.", 404)
    row["slots_left"] = max(COURSE_CAPACITY - int(row["enrolled_count"] or 0), 0)
    row["students"] = enrollment_query(where="WHERE e.course_id = ?", args=[course_pk])
    return jsonify(row)


@app.post("/api/courses")
def create_course():
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_course(data)
    if errors:
        return jsonify({"error": "Please check the course details.", "fields": errors}), 400

    cursor = get_db().execute(
        "INSERT INTO courses (course_code, course_name, department) VALUES (?, ?, ?)",
        (cleaned["course_code"], cleaned["course_name"], cleaned["department"]),
    )
    get_db().commit()
    created = query_one("SELECT * FROM courses WHERE course_id = ?", (cursor.lastrowid,))
    created["enrolled_count"] = 0
    created["slots_left"] = COURSE_CAPACITY
    return jsonify(created), 201


@app.put("/api/courses/<int:course_pk>")
def update_course(course_pk):
    if not query_one("SELECT course_id FROM courses WHERE course_id = ?", (course_pk,)):
        return fail("Course not found.", 404)

    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_course(data, course_pk)
    if errors:
        return jsonify({"error": "Please check the course details.", "fields": errors}), 400

    get_db().execute(
        "UPDATE courses SET course_code = ?, course_name = ?, department = ?"
        " WHERE course_id = ?",
        (cleaned["course_code"], cleaned["course_name"], cleaned["department"], course_pk),
    )
    get_db().commit()
    return jsonify(
        {"course_id": course_pk, "course_code": cleaned["course_code"],
         "course_name": cleaned["course_name"], "department": cleaned["department"]}
    )


@app.delete("/api/courses/<int:course_pk>")
def delete_course(course_pk):
    if not query_one("SELECT course_id FROM courses WHERE course_id = ?", (course_pk,)):
        return fail("Course not found.", 404)
    get_db().execute("DELETE FROM courses WHERE course_id = ?", (course_pk,))
    get_db().commit()
    return jsonify({"message": "Course deleted.", "course_id": course_pk})


# ---------------------------------------------------------------------------
# Enrollments (the combined feature)
# ---------------------------------------------------------------------------
def enrollment_query(where="", args=None, limit=None):
    sql = (
        "SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,"
        " s.student_id AS student_no, s.first_name, s.last_name,"
        " s.first_name || ' ' || s.last_name AS student_name,"
        " s.program, s.year_level,"
        " c.course_code, c.course_name, c.department"
        " FROM enrollments e"
        " JOIN students s ON s.id = e.student_id"
        " JOIN courses c ON c.course_id = e.course_id"
    )
    if where:
        sql += " " + where
    sql += " ORDER BY e.enrollment_id DESC"
    params = list(args or [])
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return query_all(sql, params)


@app.get("/api/enrollments")
def list_enrollments():
    clauses = []
    args = []

    search = (request.args.get("search") or "").strip()
    if search:
        like = "%" + search + "%"
        clauses.append(
            "(s.first_name LIKE ? OR s.last_name LIKE ? OR s.student_id LIKE ?"
            " OR c.course_code LIKE ? OR c.course_name LIKE ?)"
        )
        args.extend([like, like, like, like, like])

    status = (request.args.get("status") or "").strip()
    if status:
        if status not in ALLOWED_STATUSES:
            return fail("Unknown enrollment status filter.", 400)
        clauses.append("e.status = ?")
        args.append(status)

    student_pk = request.args.get("student_id")
    if student_pk:
        clauses.append("e.student_id = ?")
        args.append(int(student_pk))

    course_pk = request.args.get("course_id")
    if course_pk:
        clauses.append("e.course_id = ?")
        args.append(int(course_pk))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    limit = request.args.get("limit")
    return jsonify(enrollment_query(where=where, args=args, limit=limit))


@app.get("/api/enrollments/<int:enrollment_pk>")
def get_enrollment(enrollment_pk):
    rows = enrollment_query(where="WHERE e.enrollment_id = ?", args=[enrollment_pk])
    if not rows:
        return fail("Enrollment not found.", 404)
    return jsonify(rows[0])


@app.post("/api/enrollments")
def create_enrollment():
    data = request.get_json(silent=True) or {}
    try:
        student_pk = int(data.get("student_id"))
        course_pk = int(data.get("course_id"))
    except (TypeError, ValueError):
        return fail("A student and a course must both be selected.")

    status = str(data.get("status") or "Pending").strip()
    if status not in ALLOWED_STATUSES:
        return fail("Status must be one of: " + ", ".join(ALLOWED_STATUSES) + ".")

    if not query_one("SELECT id FROM students WHERE id = ?", (student_pk,)):
        return fail("That student does not exist.", 404)
    if not query_one("SELECT course_id FROM courses WHERE course_id = ?", (course_pk,)):
        return fail("That course does not exist.", 404)

    duplicate = query_one(
        "SELECT enrollment_id FROM enrollments WHERE student_id = ? AND course_id = ?",
        (student_pk, course_pk),
    )
    if duplicate:
        return fail("This student is already enrolled in that course.", 409)

    try:
        cursor = get_db().execute(
            "INSERT INTO enrollments (student_id, course_id, enrollment_date, status)"
            " VALUES (?, ?, ?, ?)",
            (student_pk, course_pk, today(), status),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        return fail("This student is already enrolled in that course.", 409)

    return jsonify(enrollment_query(where="WHERE e.enrollment_id = ?", args=[cursor.lastrowid])[0]), 201


@app.put("/api/enrollments/<int:enrollment_pk>")
def update_enrollment(enrollment_pk):
    if not query_one("SELECT enrollment_id FROM enrollments WHERE enrollment_id = ?", (enrollment_pk,)):
        return fail("Enrollment not found.", 404)

    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or "").strip()
    if status not in ALLOWED_STATUSES:
        return fail("Status must be one of: " + ", ".join(ALLOWED_STATUSES) + ".")

    get_db().execute(
        "UPDATE enrollments SET status = ? WHERE enrollment_id = ?", (status, enrollment_pk)
    )
    get_db().commit()
    return jsonify(enrollment_query(where="WHERE e.enrollment_id = ?", args=[enrollment_pk])[0])


@app.delete("/api/enrollments/<int:enrollment_pk>")
def delete_enrollment(enrollment_pk):
    if not query_one("SELECT enrollment_id FROM enrollments WHERE enrollment_id = ?", (enrollment_pk,)):
        return fail("Enrollment not found.", 404)
    get_db().execute("DELETE FROM enrollments WHERE enrollment_id = ?", (enrollment_pk,))
    get_db().commit()
    return jsonify({"message": "Enrollment deleted.", "enrollment_id": enrollment_pk})


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------
@app.get("/api/announcements")
def list_announcements():
    sql = "SELECT * FROM announcements ORDER BY id DESC"
    params = []
    limit = request.args.get("limit")
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    return jsonify(query_all(sql, params))


@app.get("/api/announcements/<int:announcement_pk>")
def get_announcement(announcement_pk):
    row = query_one("SELECT * FROM announcements WHERE id = ?", (announcement_pk,))
    if not row:
        return fail("Announcement not found.", 404)
    return jsonify(row)


@app.post("/api/announcements")
def create_announcement():
    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_announcement(data)
    if errors:
        return jsonify({"error": "Please check the announcement.", "fields": errors}), 400

    cursor = get_db().execute(
        "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
        (cleaned["title"], cleaned["content"], now_iso(), cleaned["author"]),
    )
    get_db().commit()
    return jsonify(query_one("SELECT * FROM announcements WHERE id = ?", (cursor.lastrowid,))), 201


@app.put("/api/announcements/<int:announcement_pk>")
def update_announcement(announcement_pk):
    if not query_one("SELECT id FROM announcements WHERE id = ?", (announcement_pk,)):
        return fail("Announcement not found.", 404)

    data = request.get_json(silent=True) or {}
    cleaned, errors = validate_announcement(data)
    if errors:
        return jsonify({"error": "Please check the announcement.", "fields": errors}), 400

    get_db().execute(
        "UPDATE announcements SET title = ?, content = ?, author = ? WHERE id = ?",
        (cleaned["title"], cleaned["content"], cleaned["author"], announcement_pk),
    )
    get_db().commit()
    return jsonify(query_one("SELECT * FROM announcements WHERE id = ?", (announcement_pk,)))


@app.delete("/api/announcements/<int:announcement_pk>")
def delete_announcement(announcement_pk):
    if not query_one("SELECT id FROM announcements WHERE id = ?", (announcement_pk,)):
        return fail("Announcement not found.", 404)
    get_db().execute("DELETE FROM announcements WHERE id = ?", (announcement_pk,))
    get_db().commit()
    return jsonify({"message": "Announcement deleted.", "id": announcement_pk})


# ---------------------------------------------------------------------------
# Small HTML frontend served by Flask (Laboratory 4 portal pages)
# ---------------------------------------------------------------------------
@app.get("/")
def page_dashboard():
    return render_template("index.html")


@app.get("/students")
def page_students():
    return render_template("students.html")


@app.get("/courses")
def page_courses():
    return render_template("courses.html")


@app.get("/enrollment")
def page_enrollment():
    return render_template("enrollment.html")


@app.get("/announcements")
def page_announcements():
    return render_template("announcements.html")


@app.context_processor
def inject_api_base():
    public = os.environ.get("PUBLIC_API_BASE", "").strip()
    return {"api_base": public or (request.url_root.rstrip("/") + "/api")}


# ---------------------------------------------------------------------------
# Error handlers keep every API response valid JSON
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def handle_404(_error):
    if request.path.startswith("/api"):
        return jsonify({"error": "Endpoint not found."}), 404
    return "Page not found.", 404


@app.errorhandler(405)
def handle_405(_error):
    if request.path.startswith("/api"):
        return jsonify({"error": "Method not allowed for this endpoint."}), 405
    return "Method not allowed.", 405


@app.errorhandler(500)
def handle_500(_error):
    if request.path.startswith("/api"):
        return jsonify({"error": "The server hit an unexpected error."}), 500
    return "Server error.", 500


# Create the database on first import so gunicorn / flask run also work.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print("Campus Connect API running on http://127.0.0.1:" + str(port))
    print("Database file:", DATABASE_PATH)
    app.run(host="0.0.0.0", port=port, debug=debug)
