"""Production settings entry point.

The base module preserves the project's existing environment variable names.
Set ``ALLOWED_HOSTS`` to a comma-separated host list in production.
"""
import os

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
    if host.strip()
] or ALLOWED_HOSTS
