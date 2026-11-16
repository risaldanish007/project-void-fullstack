import logging
from io import StringIO

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="accounts.clear_expired_sessions")
def clear_expired_sessions():
    out = StringIO()
    call_command("clearsessions", stdout=out)
    logger.info("Expired sessions cleared. %s", out.getvalue().strip())

@shared_task(name="accounts.cleanup_expired_otps")
def cleanup_expired_otps():
    out = StringIO()
    call_command("cleanup_expired_otps", stdout=out)
    logger.info(out.getvalue().strip())