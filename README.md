# Team Task Manager

Team Task Manager is a full-stack Flask web application for creating projects, managing team members, assigning tasks, and tracking task progress with Admin and Member roles.

## Features

- User signup and login
- Project creation and project dashboard
- Team member management
- Role-based access control
- Task creation, bulk assignment, priority, due date, and status tracking
- AHT-based task update control for members
- Member work submission description after AHT completion
- Dashboard metrics for projects, assigned tasks, in-progress tasks, and overdue tasks
- SQLite database with table relationships
- JSON API endpoints for projects and tasks

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- Jinja templates
- Gunicorn for Railway deployment

## Project Structure

```text
.
|-- app.py
|-- config.py
|-- database.py
|-- requirements.txt
|-- Procfile
|-- static/
|   `-- style.css
`-- templates/
    |-- base.html
    |-- dashboard.html
    |-- login.html
    |-- project.html
    `-- register.html
```

## Database Design

The application uses four main tables:

- `users`: stores registered users and hashed passwords.
- `projects`: stores project information and the project owner.
- `project_members`: connects users to projects and stores each user's role.
- `tasks`: stores task details such as title, assignee, creator, status, priority, AHT minutes, start time, submitted work description, and due date.

## Role-Based Access

- Admin users can create projects, add members, create tasks, and assign one task to multiple members at once.
- Member users can view project tasks and update tasks assigned to them.
- Member task updates are enabled only after the task's AHT time is completed.
- Members must enter a work description when submitting a completed task.
- Admin users can update any task inside their project.
- Users cannot view projects where they are not a member.
- A user can belong to only one project team, so the same user cannot be added to multiple teams with different roles.

## API Endpoints

- `GET /health` returns application health status.
- `GET /api/projects` returns projects for the logged-in user.
- `GET /api/projects/<project_id>/tasks` returns tasks for a project if the logged-in user has access.

## Run Locally

1. Create a virtual environment:

```bash
python -m venv venv
```

2. Activate it on Windows:

```bash
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the app:

```bash
python app.py
```

5. Open this URL:

```text
http://127.0.0.1:5000
```

## Railway Deployment

1. Push this project folder to GitHub.
2. Create a new Railway project.
3. Select "Deploy from GitHub repo".
4. Choose the repository.
5. Add an environment variable named `SECRET_KEY` with any long random value.
6. Railway installs dependencies from `requirements.txt`.
7. Railway starts the app using the `Procfile`.
8. Open the Railway generated domain and test signup, login, project creation, member addition, and task update.

## Demo Flow

1. Sign up as User A.
2. Create a project as User A.
3. Log out and sign up as User B.
4. Log in as User A and add User B to the project using User B's email.
5. Create a task, set AHT minutes, and assign it to one or more members using the assignee multi-select.
6. Log in as User B and update the task status.
7. Open the dashboard to show task count, in-progress count, and overdue count.
