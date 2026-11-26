# Campus Connect
## Integrated Student Enrollment and Information System

Campus Connect combines two laboratory activities into one integrated system:

* Laboratory 3 - Student Course Management API (courses, course codes, departments)
* Laboratory 4 - Campus Connect Student Information Portal (students, announcements)

The result is a single Flask REST API backed by SQLite, used by two frontends:
the HTML portal pages served by Flask itself, and the separate React dashboard
that lives in the Campus Connect web app.

All data in this project is fictional and exists only for classroom demonstration.


## 1. How the pieces fit together

    Browser (HTML pages or React dashboard)
                |
                |   HTTP requests + JSON responses (fetch)
                v
    Flask REST API ......................... app.py
                |
                |   sqlite3 module (SQL queries)
                v
    SQLite database ........................ database.db


The frontend never talks to the database directly. It sends an HTTP request such
as GET /api/students, the Flask route runs a SQL query, and the result is
returned as JSON. That is the whole idea of system integration: separate
components, one shared contract.


## 2. Project structure

    Campus-Connect/
    |
    |-- app.py                     Flask application: routes, validation, database helpers
    |-- database.db                SQLite database (created automatically on first run)
    |-- requirements.txt           Python packages needed by the project
    |-- README.md                  This file
    |-- run.bat                    Windows: start the API with the system Python
    |-- start.bat                  Windows: create a venv, install packages, start the API
    |-- render.yaml                Optional Render blueprint for deployment
    |-- .gitignore                 Files that must never be committed
    |
    |-- templates/
    |   |-- base.html              Shared layout: sidebar, top bar, API status pill
    |   |-- index.html             Dashboard page (statistics, recent activity)
    |   |-- students.html          Student management page
    |   |-- courses.html           Course management page (Laboratory 3)
    |   |-- enrollment.html        Enrollment page (the combined feature)
    |   |-- announcements.html     Announcements page (Laboratory 4)
    |
    |-- static/
    |   |-- css/style.css          Navy and white portal styling, responsive layout
    |   |-- javascript/script.js   All fetch() calls and page logic
    |   |-- images/                Optional images used by the portal
    |
    |-- screenshots/               Put your presentation screenshots here


## 3. Quick start on Windows

1. Install Python 3.10 or newer from python.org and tick "Add Python to PATH".
2. Double-click start.bat. It creates a virtual environment, installs the
   packages and starts the server.
3. Open http://127.0.0.1:5000 in your browser.
4. The database file database.db is created automatically and filled with
   fictional sample records the first time the server starts.

If you only want to start the server again later, use run.bat.


## 4. Quick start on macOS or Linux

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python app.py


## 5. REST API reference

Health and dashboard data

    GET    /api/health                     Service status, version and database name
    GET    /api/stats                      Counts used by the dashboard cards

Students

    GET    /api/students                   List students (optional ?search=)
    GET    /api/students/<id>              One student
    POST   /api/students                   Create a student
    PUT    /api/students/<id>              Update a student
    DELETE /api/students/<id>              Delete a student
    GET    /api/students/<id>/enrollments  Enrollment history of one student

Courses (Laboratory 3 contract)

    GET    /api/courses                    List courses (optional ?search=)
    GET    /api/courses/<id>               One course plus its enrolled students
    POST   /api/courses                    Create a course
    PUT    /api/courses/<id>               Update a course
    DELETE /api/courses/<id>               Delete a course

Enrollments (combined feature)

    GET    /api/enrollments                List enrollments
                                           filters: ?search= ?status= ?student_id=
                                                    ?course_id= ?limit=
    GET    /api/enrollments/<id>           One enrollment
    POST   /api/enrollments                Create an enrollment
    PUT    /api/enrollments/<id>           Update the status
    DELETE /api/enrollments/<id>           Delete an enrollment

Announcements

    GET    /api/announcements              List announcements (optional ?limit=)
    GET    /api/announcements/<id>         One announcement
    POST   /api/announcements              Create an announcement
    PUT    /api/announcements/<id>         Update an announcement
    DELETE /api/announcements/<id>         Delete an announcement

Every response is JSON. Errors always look like this:

    { "error": "This student is already enrolled in that course." }

Status codes used: 200 OK, 201 Created, 400 validation error, 404 not found,
409 duplicate enrollment, 500 unexpected server error.


## 6. Testing the API without the browser

Health check

    curl http://127.0.0.1:5000/api/health

Create a student

    curl -X POST http://127.0.0.1:5000/api/students ^
      -H "Content-Type: application/json" ^
      -d "{\"student_id\":\"2024-00199\",\"first_name\":\"Test\",\"last_name\":\"Student\",\"email\":\"test.student@campusconnect.edu.ph\",\"program\":\"BS Information Technology\",\"year_level\":\"1st Year\",\"contact_number\":\"0917-000-0000\"}"

List students

    curl http://127.0.0.1:5000/api/students


## 7. Database

SQLite file: database.db (override the location with the DATABASE_PATH
environment variable).

Tables

    students       id, student_id, first_name, last_name, email, program,
                   year_level, contact_number, created_at
    courses        course_id, course_code, course_name, department
    enrollments    enrollment_id, student_id, course_id, enrollment_date, status
    announcements  id, title, content, date_posted, author
    users          id, username, email, password_hash, role, created_at

Relationships

    enrollments.student_id -> students.id              (ON DELETE CASCADE)
    enrollments.course_id  -> courses.course_id        (ON DELETE CASCADE)
    UNIQUE (student_id, course_id) prevents duplicate enrollment

The users table is part of the required schema. It stores only a hash generated
at first run; no plaintext password exists anywhere in this repository. The
laboratory API is intentionally open, so add authentication before using it for
anything real.


## 8. Connecting the React dashboard

The Campus Connect web dashboard is a separate frontend. It reads the API base
URL from its API Setup page (default http://127.0.0.1:5000/api).

1. Start the Flask API.
2. Open the dashboard, go to API Setup, and save the API base URL.
3. The status pill turns green and every screen loads live data.

If the dashboard is served over HTTPS, the browser blocks plain HTTP requests to
127.0.0.1 (mixed content). In that case deploy the API to Render and use the
HTTPS URL instead.


## 9. Uploading to GitHub

    git init
    git add .
    git commit -m "Campus Connect: Flask REST API with SQLite"
    git branch -M main
    git remote add origin https://github.com/YOUR-USERNAME/Campus-Connect.git
    git push -u origin main

Later updates

    git add .
    git commit -m "Describe what changed"
    git push

Never commit .env files, real passwords or private API keys. The .gitignore in
this project already excludes them, together with the generated database file.


## 10. Deploying the Flask API to Render

1. Push the project to GitHub first.
2. In Render, choose New and then Web Service, and connect the repository.
3. Runtime: Python 3. Environment: Python 3.11.
4. Build command:  pip install -r requirements.txt
5. Start command:  gunicorn app:app --bind 0.0.0.0:$PORT
6. Environment variables:
       PYTHON_VERSION = 3.11.9
       DATABASE_PATH  = /var/data/database.db
       CORS_ORIGINS   = *
7. Add a persistent disk mounted at /var/data with 1 GB. Without a disk the
   SQLite file is wiped on every deploy, because the container filesystem is
   temporary.
8. Deploy, then open https://YOUR-SERVICE.onrender.com/api/health. You should
   see a JSON object with status ok.
9. In the React dashboard API Setup page, use
   https://YOUR-SERVICE.onrender.com/api as the base URL.

Notes

* Free Render instances sleep after inactivity, so the first request can take
  up to a minute. That is normal.
* The Flask portal pages are also served by Render at the root URL, so the
  whole laboratory project is reachable from one address.


## 11. Presentation checklist

1. Start the API, open the dashboard, point out the four statistic cards.
2. Add a student and show the new row in the students table.
3. Add a course and show it in the catalog.
4. Edit the course code, then delete a course you created.
5. Enroll a student and show the new enrollment row with status Pending.
6. Change the status to Approved and show the badge update.
7. Try enrolling the same student twice and show the duplicate error message.
8. Post an announcement and show it on the dashboard.
9. Open a student profile and show the enrollment history.
10. Open database.db in DB Browser for SQLite to prove the rows really exist.

Fictional sample data included: 6 students, 6 courses, 7 enrollments and
3 announcements.
