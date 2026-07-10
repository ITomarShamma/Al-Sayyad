"""Production settings: PostgreSQL, debug off, HTTPS hardening.

Every sensitive value is read from the environment (.env on the server).
Run the server with:  DJANGO_SETTINGS_MODULE=config.settings.prod
"""

from .base import *  # noqa: F401,F403
from .base import env, env_bool

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "alsayyad"),
        "USER": env("DB_USER", "alsayyad"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
    }
}

# Shared cache: login rate-limit counters (M25) must be shared across all
# Gunicorn workers — the default LocMem cache is per-process, which would
# multiply the allowed attempts by the worker count. DatabaseCache is exact,
# needs no extra service, and requires a one-time:
#   python manage.py createcachetable
# (Upgrade to Redis later only if cache traffic ever becomes a bottleneck.)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# Security hardening — assumes the site runs behind HTTPS in production.
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Trust the reverse proxy's HTTPS header (Nginx/Caddy in front of the app).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
