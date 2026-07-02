"""
Base settings shared by every environment.

Environment-specific overrides live in ``dev.py`` (local development) and
``prod.py`` (production). Secrets and per-machine values come from a ``.env``
file that is never committed to git.

Which settings module is used is decided by ``DJANGO_SETTINGS_MODULE``:
  - ``manage.py``            -> config.settings.dev   (local)
  - ``config/wsgi|asgi.py``  -> config.settings.prod  (server)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: .../Al-Sayyad/  (three levels up from this file).
BASE_DIR = Path(__file__).resolve().parents[2]

# Load variables from the .env file (if it exists) into the environment.
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    """Read an environment variable, returning ``default`` when unset."""
    return os.environ.get(key, default)


def env_bool(key, default=False):
    """Read an environment variable as a boolean (1/true/yes/on)."""
    return str(env(key, default)).strip().lower() in {"1", "true", "yes", "on"}


# --- Security -------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]


# --- Applications ---------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Our own apps. Each one is a self-contained module of the store.
LOCAL_APPS = [
    "apps.core",      # shared helpers, base models, context processors
    "apps.pages",     # homepage and static pages
    "apps.catalog",   # categories and products
    "apps.cart",      # shopping cart
    "apps.orders",    # orders, checkout, payment (COD now, ShamCash later)
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # picks the request language (ar/en)
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",  # {% trans %} + LANGUAGE_CODE
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --- Password validation --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Internationalization (Arabic-first, English-ready) -------------------
LANGUAGE_CODE = "ar"            # default UI language
TIME_ZONE = "Asia/Damascus"    # Syria
USE_I18N = True
USE_TZ = True

# Languages the site can be shown in.
# Arabic only for now: LocaleMiddleware negotiates the language per request
# from the browser's Accept-Language header — if "en" were listed here,
# English-preferring browsers would get dir=ltr while the content is still
# Arabic (no translations yet). Add ("en", "English") back once the English
# translation files actually exist.
LANGUAGES = [
    ("ar", "العربية"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]


# --- Static & media files -------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]      # our source assets (css/js/fonts/img)
STATIC_ROOT = BASE_DIR / "staticfiles"        # collected assets for production

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"               # user-uploaded files (product images)


# --- Misc -----------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
