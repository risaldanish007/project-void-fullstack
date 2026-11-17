import os
from celery import Celery

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    raise RuntimeError(
        "Set DJANGO_SETTINGS_MODULE before starting Celery; use "
        "config.settings.production for deployment."
    )

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
