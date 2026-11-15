"""Production settings. Configure all required values through the environment."""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False


def required_csv(name):
    values = [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]
    if not values:
        raise ImproperlyConfigured(f"{name} must contain at least one value.")
    return values


ALLOWED_HOSTS = required_csv("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = required_csv("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = required_csv("CSRF_TRUSTED_ORIGINS")

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
