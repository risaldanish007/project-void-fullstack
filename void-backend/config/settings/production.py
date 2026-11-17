"""Production settings. Configure all required values through the environment."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

if os.environ.get("DJANGO_SETTINGS_MODULE") != "config.settings.production":
    raise ImproperlyConfigured(
        "Set DJANGO_SETTINGS_MODULE=config.settings.production before starting production processes."
    )


def required_value(name):
    value = os.environ.get(name, "").strip()
    if not value or value.lower().startswith(("replace-", "change-me", "your-")):
        raise ImproperlyConfigured(f"{name} must be set to a real production value.")
    return value


SECRET_KEY = required_value("SECRET_KEY")
for variable in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST"):
    required_value(variable)


def required_csv(name):
    values = [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]
    if not values:
        raise ImproperlyConfigured(f"{name} must contain at least one value.")
    return values


ALLOWED_HOSTS = required_csv("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = required_csv("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = required_csv("CSRF_TRUSTED_ORIGINS")
if any("*" in host or "://" in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("ALLOWED_HOSTS must contain exact hostnames, without schemes or wildcards.")
if any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS + CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production CORS and CSRF origins must use HTTPS.")

# The application is expected to run behind a TLS-terminating proxy/load balancer.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() == "true"
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "false").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")
if not CELERY_BROKER_URL:
    raise ImproperlyConfigured("CELERY_BROKER_URL must be set in production.")
if not CELERY_BROKER_URL.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("CELERY_BROKER_URL must use Redis or TLS Redis.")

CACHE_REDIS_URL = required_value("CACHE_REDIS_URL")
if not CACHE_REDIS_URL.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("CACHE_REDIS_URL must use Redis or TLS Redis.")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_REDIS_URL,
        "KEY_PREFIX": "void",
    }
}

for variable in (
    "EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
    "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
):
    required_value(variable)

for directory in ("MEDIA_ROOT", "STATIC_ROOT"):
    path = required_value(directory)
    if not os.path.isabs(path):
        raise ImproperlyConfigured(f"{directory} must be an absolute persistent path in production.")

if COOKIE_SAMESITE not in {"Lax", "Strict", "None"}:
    raise ImproperlyConfigured("COOKIE_SAMESITE must be Lax, Strict, or None.")
if COOKIE_SAMESITE == "None" and not (SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE):
    raise ImproperlyConfigured("SameSite=None cookies require Secure cookies.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
DATABASES["default"]["CONN_MAX_AGE"] = int(os.environ.get("DB_CONN_MAX_AGE", "60"))
