import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from ..catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PLACED = "placed", "Placed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUND_PENDING = "refund_pending", "Refund pending"
        REFUNDED = "refunded", "Refunded"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # Snapshot customer details so later account changes do not alter the order.
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()

    # Shipping address snapshot.
    shipping_first_name = models.CharField(max_length=100)
    shipping_last_name = models.CharField(max_length=100)
    shipping_phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_instructions = models.TextField(blank=True)

    # Price snapshot: Product prices are USD; payment is collected in INR.
    currency = models.CharField(max_length=3, default="INR")
    subtotal_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    exchange_rate_usd_to_inr = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.000001"))],
    )
    total_inr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # Set by the backend during Razorpay order creation and payment verification.
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    inventory_deducted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.public_id} — {self.user}"


class RazorpayPaymentEvent(models.Model):
    """Minimal payment idempotency ledger; never store raw gateway payloads."""

    event_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
    payment_id = models.CharField(max_length=100, unique=True)
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="payment_events",
    )
    refund_required = models.BooleanField(default=False)
    refund_id = models.CharField(max_length=100, blank=True)
    refund_processed = models.BooleanField(default=False)
    refund_attempted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class RazorpayWebhookReceipt(models.Model):
    event_id = models.CharField(max_length=128, unique=True)
    event_type = models.CharField(max_length=80)
    payment_id = models.CharField(max_length=100, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    unit_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    unit_price_inr = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"
