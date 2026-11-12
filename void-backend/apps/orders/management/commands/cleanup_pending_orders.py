import logging
from datetime import timedelta

import razorpay
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Product
from apps.orders.models import Order


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Release stock reserved by expired unpaid orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=15,
            help="Age in minutes before a pending order can expire. Default: 15.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report eligible orders without changing stock or orders.",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]

        if minutes < 1:
            raise CommandError("--minutes must be at least 1.")

        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise CommandError("Razorpay credentials are not configured.")

        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        cutoff = timezone.now() - timedelta(minutes=minutes)

        candidates = Order.objects.filter(
            status=Order.Status.PENDING_PAYMENT,
            payment_status=Order.PaymentStatus.PENDING,
            inventory_deducted=True,
            created_at__lt=cutoff,
        )

        released_count = 0
        skipped_count = 0

        for candidate in candidates.iterator():
            if not candidate.razorpay_order_id:
                skipped_count += 1
                continue

            # Keep stock reserved if Razorpay reports any attempt that is not
            # definitively failed, or if the Razorpay status check errors.
            try:
                result = client.order.payments(candidate.razorpay_order_id)
                payments = result.get("items", [])
            except Exception:
                logger.exception(
                    "Could not check Razorpay payments for order %s",
                    candidate.public_id,
                )
                skipped_count += 1
                continue

            if any(payment.get("status") != "failed" for payment in payments):
                skipped_count += 1
                continue

            if options["dry_run"]:
                self.stdout.write(
                    f"Order {candidate.public_id} is eligible for stock release."
                )
                released_count += 1
                continue

            with transaction.atomic():
                order = (
                    Order.objects.select_for_update()
                    .filter(pk=candidate.pk)
                    .first()
                )

                # Recheck after acquiring the lock; payment verification may
                # have completed while the Razorpay request was in progress.
                if (
                    order is None
                    or order.status != Order.Status.PENDING_PAYMENT
                    or order.payment_status != Order.PaymentStatus.PENDING
                    or not order.inventory_deducted
                    or order.created_at >= cutoff
                ):
                    skipped_count += 1
                    continue

                order_items = list(order.items.all())
                product_ids = {
                    item.product_id
                    for item in order_items
                    if item.product_id is not None
                }

                products = {
                    product.pk: product
                    for product in Product.objects.select_for_update()
                    .filter(pk__in=product_ids)
                    .order_by("pk")
                }

                for item in order_items:
                    product = products.get(item.product_id)
                    if product is not None:
                        product.stock += item.quantity
                        product.save(update_fields=["stock"])

                order.status = Order.Status.CANCELLED
                order.inventory_deducted = False
                order.save(update_fields=[
                    "status",
                    "inventory_deducted",
                    "updated_at",
                ])

                released_count += 1

        if options["dry_run"]:
            self.stdout.write(
                f"{released_count} expired order(s) would release stock; "
                f"{skipped_count} skipped."
            )
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Released stock for {released_count} expired order(s); "
                f"{skipped_count} skipped."
            ))
