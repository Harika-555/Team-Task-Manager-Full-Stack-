# Interview Notes

Use this file to understand the project and prepare for explanation during the interview.

## 1. Project Explanation

This project is a team task manager. A user can sign up, log in, create a project, add team members, create tasks, assign tasks to members, and track task status. The app supports two roles: Admin and Member.

Simple explanation:

"I built a Flask-based full-stack task manager where users can create projects and manage team tasks. I used SQLite for storing users, projects, project members, and tasks. I also added role-based access so only Admin users can add members and create tasks, while Members can update assigned task statuses."

## 2. Technologies Used

Python:
The main programming language used for backend logic.

Flask:
A lightweight Python web framework used to create routes, handle forms, manage sessions, and return pages or JSON responses.

SQLite:
A small SQL database used to store application data. It is file-based, so it is easy for a small assignment project.

HTML:
Used to structure pages like login, signup, dashboard, and project detail.

CSS:
Used to style the user interface.

Jinja:
Flask's template engine. It lets the backend pass data into HTML pages.

Werkzeug password hashing:
Used to hash passwords before storing them. The app does not store plain text passwords.

Gunicorn:
A production web server used by Railway to run the Flask app.

Railway:
A deployment platform used to host the live application.

## 3. Main Files

`app.py`:
Contains routes, authentication logic, project logic, task logic, role checks, and API endpoints.

`database.py`:
Creates the database connection and initializes all database tables.

`config.py`:
Stores configuration such as secret key and database path.

`templates/`:
Contains HTML pages rendered by Flask.

`static/style.css`:
Contains styling for the web pages.

`requirements.txt`:
Lists Python packages needed to run the project.

`Procfile`:
Tells Railway how to start the app.

## 4. Database Relationships

`users` table:
Stores user name, email, and password hash.

`projects` table:
Stores project name, description, and owner id.

`project_members` table:
Connects users and projects. It also stores the role for each user in a project.

`tasks` table:
Stores each task and connects it to a project, assignee, and creator.

Important relationship:
One project can have many members. One project can have many tasks. One task belongs to one project and can be assigned to one user.

## 5. Role-Based Access Control

Admin:
Can create a project, add members, create tasks, assign tasks, and update any task in that project.

Member:
Can view project details and update tasks assigned to them.

Access control example:
Before showing a project, the app checks whether the logged-in user exists in the `project_members` table for that project.

Extra rule:
A user can belong to only one project team. If a user is already Admin or Member in one project, another Admin cannot add that same user to another project. This keeps roles unique and avoids duplicate team memberships.

## 6. Authentication Flow

Signup:
The user enters name, email, and password. The password is hashed and saved in the database.

Login:
The app checks the email and verifies the password hash. If correct, it stores the user id in the session.

Session:
Session stores the logged-in user's id so Flask can identify the user on later requests.

Logout:
The session is cleared.

## 7. REST API Endpoints

`GET /health`:
Returns `{ "status": "ok" }` and is useful for deployment checks.

`GET /api/projects`:
Returns projects available to the logged-in user.

`GET /api/projects/<project_id>/tasks`:
Returns tasks for a project only if the logged-in user has access to that project.

## 8. Validations

The app validates required fields such as name, email, password, project name, task title, assignee, role, priority, status, and due date.

Examples:
- Password must be at least 6 characters.
- Project name is required.
- Task title and assignee are required.
- Role must be Admin or Member.
- Status must be To Do, In Progress, or Done.
- Priority must be Low, Medium, or High.
- Due date must be a valid date.

## 9. Questions You May Be Asked

What is Flask?
Flask is a lightweight Python web framework used to build web applications and APIs.

Why did you use SQLite?
SQLite is simple, serverless, and good for a small assignment project. It supports SQL tables and relationships.

How are passwords stored?
Passwords are stored as hashes using Werkzeug. The original password is never stored.

What is role-based access control?
It means different users have different permissions. In this app, Admins can manage projects and tasks, while Members have limited task update access.

What is a foreign key?
A foreign key connects one table to another. For example, `tasks.project_id` connects a task to a project.

What is a REST API?
A REST API exposes application data through URLs using HTTP methods like GET and POST. This app has JSON endpoints for projects and tasks.

What happens after login?
The app stores the user id in a session. Later routes use that id to fetch the current user and check permissions.

How do you track overdue tasks?
The app compares a task's due date with today's date. If the due date is before today and the task is not Done, it is counted as overdue.

## 10. Demo Script

1. Open the live URL.
2. Sign up as an admin user.
3. Create a project.
4. Sign up as a second user.
5. Log in as the admin again.
6. Add the second user to the project.
7. Create a task and assign it to the second user.
8. Log in as the second user.
9. Update the task status.
10. Show the dashboard metrics and task board.
