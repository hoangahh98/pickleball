import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path=".env"):
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_dotenv()

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "postgres"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT", "5432"),
}

# ============ FLASK CONFIG ============
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
DEBUG = False  # Set True only when developing locally

# ============ FILE UPLOAD CONFIG ============
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# ============ APP SETTINGS ============
APP_NAME = "Pickleball Tournament Manager"
APP_VERSION = "1.0.0"
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
