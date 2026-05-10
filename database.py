import os
import sqlite3
from typing import Optional

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        database_path = current_app.config["DATABASE_PATH"]
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode = OFF")
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_: Optional[BaseException] = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Member')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, user_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            assignee_id INTEGER,
            created_by INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('To Do', 'In Progress', 'Done')),
            priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
            due_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (assignee_id) REFERENCES users(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        """
    )
    db.commit()
