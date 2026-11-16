import logging
from io import StringIO

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="cart.cleanup_guest_carts")
def cleanup_guest_carts():
    out = StringIO()
    call_command("cleanup_guest_carts", stdout=out)
    logger.info(out.getvalue().strip())