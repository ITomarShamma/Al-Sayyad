"""Development settings: SQLite database, debug on, local hosts."""

from .base import *  # noqa: F401,F403  (re-export every base setting)
from .base import BASE_DIR

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Zero-config local database. Switching to PostgreSQL later only changes prod.py.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
