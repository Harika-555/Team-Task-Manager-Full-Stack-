import os
import sqlite3
from datetime import date

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import close_db, get_db, init_db


app = Flask(__name__)
app.config.from_object(Config)
app.teardown_appcontext(close_db)

PROJECT_ROLES = ("Admin", "Member")
TASK_STATUSES = ("To Do", "In Progress", "Done")
TASK_PRIORITIES = ("Low", "Medium", "High")
MAX_NAME_LENGTH = 80
MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 500
MAX_AHT_MINUTES = 1440


def create_database_if_needed() -> None:
    with app.app_context():
        init_db()


create_database_if_needed()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = get_db()
    return db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required_user():
    user = get_current_user()
    if user is None:
        flash("Please login to continue.", "error")
        return None
    return user


def get_project_for_user(project_id: int, user_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT p.*, pm.role AS current_user_role
        FROM projects p
        JOIN project_members pm ON pm.project_id = p.id
        WHERE p.id = ? AND pm.user_id = ?
        """,
        (project_id, user_id),
    ).fetchone()


def project_members(project_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT u.id, u.name, u.email, pm.role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id = ?
        ORDER BY pm.role, u.name
        """,
        (project_id,),
    ).fetchall()


def assignable_members(project_id: int, current_user_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT u.id, u.name, u.email, pm.role
        FROM project_members pm
        JOIN users u ON u.id = pm.user_id
        WHERE pm.project_id = ? AND u.id != ?
        ORDER BY u.name
        """,
        (project_id, current_user_id),
    ).fetchall()


def user_project_membership(user_id: int):
    db = get_db()
    return db.execute(
        """
        SELECT pm.project_id, pm.role, p.name AS project_name
        FROM project_members pm
        JOIN projects p ON p.id = pm.project_id
        WHERE pm.user_id = ?
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()


def role_label(role: str) -> str:
    return "an Admin" if role == "Admin" else "a team member"


def parse_due_date(raw_due_date: str):
    raw_due_date = raw_due_date.strip()
    if not raw_due_date:
        return None
    try:
        return date.fromisoformat(raw_due_date).isoformat()
    except ValueError as exc:
        raise ValueError("Due date must be a valid calendar date.") from exc


def parse_aht_minutes(raw_aht: str) -> int:
    raw_aht = raw_aht.strip()
    if not raw_aht:
        return 0
    try:
        aht_minutes = int(raw_aht)
    except ValueError as exc:
        raise ValueError("AHT must be a whole number of minutes.") from exc
    if aht_minutes < 0 or aht_minutes > MAX_AHT_MINUTES:
        raise ValueError("AHT must be between 0 and 1440 minutes.")
    return aht_minutes


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("register"))


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
        elif len(name) > MAX_NAME_LENGTH:
            flash("Name must be 80 characters or less.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                db.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email already exists. Try another one.", "error")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
        else:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    db = get_db()
    projects = db.execute(
        """
        SELECT p.*, pm.role AS current_user_role,
            COUNT(t.id) AS task_count,
            SUM(CASE WHEN t.status = 'Done' THEN 1 ELSE 0 END) AS done_count
        FROM projects p
        JOIN project_members pm ON pm.project_id = p.id
        LEFT JOIN tasks t ON t.project_id = p.id
        WHERE pm.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    assigned_tasks = db.execute(
        """
        SELECT t.*, p.name AS project_name
        FROM tasks t
        JOIN projects p ON p.id = t.project_id
        WHERE t.assignee_id = ?
        ORDER BY
            CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END,
            t.due_date ASC,
            t.created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    today = date.today().isoformat()
    metrics = {
        "projects": len(projects),
        "assigned": len(assigned_tasks),
        "in_progress": sum(1 for task in assigned_tasks if task["status"] == "In Progress"),
        "overdue": sum(
            1
            for task in assigned_tasks
            if task["due_date"] and task["due_date"] < today and task["status"] != "Done"
        ),
    }

    return render_template(
        "dashboard.html",
        user=user,
        projects=projects,
        assigned_tasks=assigned_tasks,
        metrics=metrics,
        today=today,
    )


@app.route("/projects", methods=["POST"])
def create_project():
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("dashboard"))
    if len(name) > MAX_TITLE_LENGTH:
        flash("Project name must be 120 characters or less.", "error")
        return redirect(url_for("dashboard"))
    if len(description) > MAX_DESCRIPTION_LENGTH:
        flash("Project description must be 500 characters or less.", "error")
        return redirect(url_for("dashboard"))

    existing_membership = user_project_membership(user["id"])
    if existing_membership is not None:
        flash("You already belong to a project team. One user can have only one project role.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    cursor = db.execute(
        "INSERT INTO projects (name, description, owner_id) VALUES (?, ?, ?)",
        (name, description, user["id"]),
    )
    project_id = cursor.lastrowid
    db.execute(
        "INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
        (project_id, user["id"], "Admin"),
    )
    db.commit()
    flash("Project created. You are the project admin.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    project = get_project_for_user(project_id, user["id"])
    if project is None:
        flash("You do not have access to this project.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    tasks = db.execute(
        """
        SELECT t.*, assignee.name AS assignee_name, creator.name AS creator_name,
            CASE
                WHEN t.aht_minutes = 0
                    OR strftime('%s', 'now') >= strftime('%s', t.created_at) + (t.aht_minutes * 60)
                THEN 1
                ELSE 0
            END AS aht_ready,
            datetime(t.created_at, '+' || t.aht_minutes || ' minutes') AS aht_available_at
        FROM tasks t
        LEFT JOIN users assignee ON assignee.id = t.assignee_id
        JOIN users creator ON creator.id = t.created_by
        WHERE t.project_id = ?
        ORDER BY
            CASE t.status WHEN 'To Do' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END,
            CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END,
            t.due_date ASC
        """,
        (project_id,),
    ).fetchall()
    members = project_members(project_id)
    assignees = assignable_members(project_id, user["id"])
    today = date.today().isoformat()

    return render_template(
        "project.html",
        project=project,
        tasks=tasks,
        members=members,
        assignees=assignees,
        roles=PROJECT_ROLES,
        statuses=TASK_STATUSES,
        priorities=TASK_PRIORITIES,
        today=today,
    )


@app.route("/api/projects")
def api_projects():
    user = login_required_user()
    if user is None:
        return jsonify({"error": "Authentication required"}), 401

    db = get_db()
    projects = db.execute(
        """
        SELECT p.id, p.name, p.description, pm.role AS role, p.created_at
        FROM projects p
        JOIN project_members pm ON pm.project_id = p.id
        WHERE pm.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    return jsonify([dict(project) for project in projects])


@app.route("/api/projects/<int:project_id>/tasks")
def api_project_tasks(project_id):
    user = login_required_user()
    if user is None:
        return jsonify({"error": "Authentication required"}), 401

    project = get_project_for_user(project_id, user["id"])
    if project is None:
        return jsonify({"error": "Project not found or access denied"}), 404

    db = get_db()
    tasks = db.execute(
        """
        SELECT t.id, t.title, t.description, t.status, t.priority, t.due_date,
            assignee.name AS assignee_name
        FROM tasks t
        LEFT JOIN users assignee ON assignee.id = t.assignee_id
        WHERE t.project_id = ?
        ORDER BY t.created_at DESC
        """,
        (project_id,),
    ).fetchall()
    return jsonify([dict(task) for task in tasks])


@app.route("/projects/<int:project_id>/members", methods=["POST"])
def add_member(project_id):
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    project = get_project_for_user(project_id, user["id"])
    if project is None or project["current_user_role"] != "Admin":
        flash("Only project admins can add team members.", "error")
        return redirect(url_for("dashboard"))

    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "Member")
    if role not in PROJECT_ROLES:
        flash("Invalid project role.", "error")
        return redirect(url_for("project_detail", project_id=project_id))

    db = get_db()
    member = db.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()
    if member is None:
        flash("Ask the teammate to sign up first, then add their email.", "error")
        return redirect(url_for("project_detail", project_id=project_id))

    existing_membership = user_project_membership(member["id"])
    if existing_membership is not None:
        existing_role = role_label(existing_membership["role"])
        if existing_membership["project_id"] == project_id:
            message = f"{member['name']} is already {existing_role} in this team."
        else:
            message = (
                f"{member['name']} is already {existing_role} of another team: "
                f"{existing_membership['project_name']}."
            )
        flash(message, "error")
        return redirect(url_for("project_detail", project_id=project_id))

    try:
        db.execute(
            "INSERT INTO project_members (project_id, user_id, role) VALUES (?, ?, ?)",
            (project_id, member["id"], role),
        )
        db.commit()
        flash("Team member added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("This user is already part of the project.", "error")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/tasks", methods=["POST"])
def create_task(project_id):
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    project = get_project_for_user(project_id, user["id"])
    if project is None or project["current_user_role"] != "Admin":
        flash("Only project admins can create and assign tasks.", "error")
        return redirect(url_for("dashboard"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    assignee_ids = [assignee_id.strip() for assignee_id in request.form.getlist("assignee_ids") if assignee_id.strip()]
    priority = request.form.get("priority", "Medium")
    raw_aht_minutes = request.form.get("aht_minutes", "")
    raw_due_date = request.form.get("due_date", "")

    if not title or not assignee_ids:
        flash("Task title and at least one assignee are required.", "error")
        return redirect(url_for("project_detail", project_id=project_id))
    if len(title) > MAX_TITLE_LENGTH:
        flash("Task title must be 120 characters or less.", "error")
        return redirect(url_for("project_detail", project_id=project_id))
    if len(description) > MAX_DESCRIPTION_LENGTH:
        flash("Task description must be 500 characters or less.", "error")
        return redirect(url_for("project_detail", project_id=project_id))
    if priority not in TASK_PRIORITIES:
        flash("Invalid priority.", "error")
        return redirect(url_for("project_detail", project_id=project_id))

    try:
        due_date = parse_due_date(raw_due_date)
        aht_minutes = parse_aht_minutes(raw_aht_minutes)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("project_detail", project_id=project_id))

    db = get_db()
    unique_assignee_ids = list(dict.fromkeys(assignee_ids))
    placeholders = ",".join("?" for _ in unique_assignee_ids)
    valid_assignees = db.execute(
        f"""
        SELECT user_id
        FROM project_members
        WHERE project_id = ? AND user_id != ? AND user_id IN ({placeholders})
        """,
        (project_id, user["id"], *unique_assignee_ids),
    ).fetchall()
    valid_assignee_ids = {str(assignee["user_id"]) for assignee in valid_assignees}
    if len(valid_assignee_ids) != len(unique_assignee_ids):
        flash("Tasks can only be assigned to other project members.", "error")
        return redirect(url_for("project_detail", project_id=project_id))

    task_rows = [
        (project_id, title, description, assignee_id, user["id"], "To Do", priority, aht_minutes, due_date)
        for assignee_id in unique_assignee_ids
    ]
    db.executemany(
        """
        INSERT INTO tasks (
            project_id, title, description, assignee_id, created_by,
            status, priority, aht_minutes, due_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        task_rows,
    )
    db.commit()
    if len(task_rows) == 1:
        flash("Task created and assigned.", "success")
    else:
        flash(f"Task created and assigned to {len(task_rows)} members.", "success")
    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    user = login_required_user()
    if user is None:
        return redirect(url_for("login"))

    status = request.form.get("status", "")
    if status not in TASK_STATUSES:
        flash("Invalid task status.", "error")
        return redirect(url_for("dashboard"))

    db = get_db()
    task = db.execute(
        """
        SELECT t.*, pm.role AS current_user_role
        FROM tasks t
        JOIN project_members pm ON pm.project_id = t.project_id
        WHERE t.id = ? AND pm.user_id = ?
        """,
        (task_id, user["id"]),
    ).fetchone()
    if task is None:
        flash("Task not found or access denied.", "error")
        return redirect(url_for("dashboard"))
    if task["assignee_id"] != user["id"] and task["current_user_role"] != "Admin":
        flash("Only the assignee or an admin can update this task.", "error")
        return redirect(url_for("project_detail", project_id=task["project_id"]))
    if task["current_user_role"] != "Admin" and task["aht_minutes"] > 0:
        aht_ready = db.execute(
            """
            SELECT CASE
                WHEN strftime('%s', 'now') >= strftime('%s', created_at) + (aht_minutes * 60)
                THEN 1
                ELSE 0
            END AS ready
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        if aht_ready is None or not aht_ready["ready"]:
            flash("You can update this task only after its AHT time is completed.", "error")
            return redirect(url_for("project_detail", project_id=task["project_id"]))

    db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    db.commit()
    flash("Task status updated.", "success")
    return redirect(url_for("project_detail", project_id=task["project_id"]))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    create_database_if_needed()
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
