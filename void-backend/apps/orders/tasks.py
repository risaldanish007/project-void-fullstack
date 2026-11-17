import logging
from io import StringIO

from celery import shared_task
import razorpay
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import RazorpayPaymentEvent, Order

logger = logging.getLogger(__name__)


@shared_task(name="orders.cleanup_pending_orders")
def cleanup_pending_orders():
    out = StringIO()
    call_command("cleanup_pending_orders", stdout=out)
    logger.info(out.getvalue().strip())


@shared_task(name="orders.refund_captured_payment", bind=True, max_retries=8)
def refund_captured_payment(self, event_id):
    """Retry safe full refunds; receipt lookup makes an ambiguous retry idempotent."""
    with transaction.atomic():
        event = RazorpayPaymentEvent.objects.select_for_update().get(pk=event_id)
        if not event.refund_required:
            return "already settled"
        now = timezone.now()
        if event.refund_attempted_at and event.refund_attempted_at > now - timedelta(minutes=4):
            return "refund already in progress"
        event.refund_attempted_at = now
        event.save(update_fields=["refund_attempted_at", "updated_at"])
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment = client.payment.fetch(event.payment_id)
        amount = int(payment["amount"])
        receipt = f"void-refund-{event.pk}"
        refunds = client.payment.fetch_multiple_refund(event.payment_id, {"count": 100})
        refund = next((item for item in refunds.get("items", []) if item.get("receipt") == receipt), None)
        if refund is None:
            remaining = amount - int(payment.get("amount_refunded", 0))
            if remaining <= 0:
                refund = {"id": "", "status": "processed"}
            else:
                refund = client.payment.refund(event.payment_id, {
                    "amount": remaining, "receipt": receipt,
                })
        with transaction.atomic():
            if event.order_id:
                Order.objects.select_for_update().filter(pk=event.order_id).first()
            locked = RazorpayPaymentEvent.objects.select_for_update().get(pk=event.pk)
            locked.refund_id = refund.get("id", locked.refund_id)
            locked.refund_processed = refund.get("status") == "processed"
            if locked.refund_processed:
                locked.refund_required = False
            locked.save(update_fields=[
                "refund_id", "refund_processed", "refund_required", "updated_at",
            ])
            if locked.refund_processed and locked.order_id:
                order = Order.objects.select_for_update().get(pk=locked.order_id)
                if (order.payment_status == Order.PaymentStatus.REFUND_PENDING
                        and order.razorpay_payment_id == locked.payment_id):
                    order.payment_status = Order.PaymentStatus.REFUNDED
                    order.save(update_fields=["payment_status", "updated_at"])
        return locked.refund_id
    except Exception as exc:
        logger.exception("Refund attempt failed for payment event %s", event_id)
        raise self.retry(exc=exc, countdown=300)


@shared_task(name="orders.retry_pending_refunds")
def retry_pending_refunds():
    stale_before = timezone.now() - timedelta(minutes=4)
    ids = list(RazorpayPaymentEvent.objects.filter(
        refund_required=True,
    ).filter(
        Q(refund_attempted_at__isnull=True)
        | Q(refund_attempted_at__lt=stale_before)
    ).values_list("pk", flat=True)[:100])
    for event_id in ids:
        refund_captured_payment.delay(event_id)
