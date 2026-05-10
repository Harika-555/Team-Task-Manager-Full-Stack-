import os


class Config:
    APP_DATA_DIR = os.path.join(os.path.dirname(__file__), "instance")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-before-deployment")
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        os.path.join(APP_DATA_DIR, "task_manager_app.db"),
    )
