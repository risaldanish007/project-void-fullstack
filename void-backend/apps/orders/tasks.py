import logging
from io import StringIO

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="orders.cleanup_pending_orders")
def cleanup_pending_orders():
    out = StringIO()
    call_command("cleanup_pending_orders", stdout=out)
    logger.info(out.getvalue().strip())