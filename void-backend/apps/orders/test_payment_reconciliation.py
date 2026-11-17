import hashlib
import hmac
import json
import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, RazorpayPaymentEvent, RazorpayWebhookReceipt
from apps.orders.payment_service import InvalidCapturedPayment, reconcile_captured_payment


class PaymentReconciliationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="buyer@example.test", password="pass")
        self.category = Category.objects.create(name="Energy")
        self.product = Product.objects.create(
            name="VOID Can", description="can", price=Decimal("2.00"),
            category=self.category, series=Product.Series.VOID, stock=6,
        )
        self.order = Order.objects.create(
            user=self.user, customer_name="Buyer", customer_email=self.user.email,
            shipping_first_name="Buyer", shipping_last_name="", shipping_phone="123",
            shipping_address="1 Main", shipping_city="City", shipping_state="State",
            shipping_postal_code="00000", currency="INR", subtotal_usd=Decimal("2.00"),
            exchange_rate_usd_to_inr=Decimal("83.000000"), total_inr=Decimal("166.00"),
            razorpay_order_id="order_test", inventory_deducted=True,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name=self.product.name,
            quantity=2, unit_price_usd=Decimal("2.00"), unit_price_inr=Decimal("166.00"),
        )
        self.payment = {
            "id": "pay_test", "order_id": "order_test", "status": "captured",
            "amount": 16600, "currency": "INR",
        }

    def test_captured_payment_settles_once(self):
        order, _, settled = reconcile_captured_payment(self.payment, "evt_test")
        self.assertTrue(settled)
        self.assertEqual(order.status, Order.Status.PLACED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)  # settlement must not reserve twice
        _, _, repeated = reconcile_captured_payment(self.payment, "evt_test")
        self.assertFalse(repeated)
        self.assertEqual(RazorpayPaymentEvent.objects.count(), 1)

    def test_invalid_amount_does_not_create_event_or_settle(self):
        bad = {**self.payment, "amount": 1}
        with self.assertRaises(InvalidCapturedPayment):
            reconcile_captured_payment(bad, "evt_bad")
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)
        self.assertFalse(RazorpayPaymentEvent.objects.exists())

    def test_late_capture_reacquires_stock_or_records_refund(self):
        self.product.stock = 0
        self.product.save(update_fields=["stock"])
        self.order.inventory_deducted = False
        self.order.status = Order.Status.CANCELLED
        self.order.save(update_fields=["inventory_deducted", "status"])
        order, event, settled = reconcile_captured_payment(self.payment, "evt_late")
        self.assertFalse(settled)
        self.assertTrue(event.refund_required)
        self.assertEqual(order.payment_status, Order.PaymentStatus.REFUND_PENDING)
        self.assertEqual(order.status, Order.Status.CANCELLED)


@override_settings(RAZORPAY_WEBHOOK_SECRET="test-webhook-secret")
class RazorpayWebhookTests(PaymentReconciliationTests):
    def test_signature_validation_and_event_deduplication(self):
        body = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": self.payment}},
        }).encode()
        signature = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
        client = APIClient()
        invalid = client.generic(
            "POST", "/api/v1/orders/webhooks/razorpay/", body,
            content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE="wrong",
            HTTP_X_RAZORPAY_EVENT_ID="evt_webhook",
        )
        self.assertEqual(invalid.status_code, 400)
        valid = client.generic(
            "POST", "/api/v1/orders/webhooks/razorpay/", body,
            content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_webhook",
        )
        self.assertEqual(valid.status_code, 200)
        duplicate = client.generic(
            "POST", "/api/v1/orders/webhooks/razorpay/", body,
            content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_webhook",
        )
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(RazorpayPaymentEvent.objects.count(), 1)
        self.assertEqual(RazorpayWebhookReceipt.objects.count(), 1)

    def test_callback_then_webhook_does_not_settle_twice(self):
        reconcile_captured_payment(self.payment)
        body = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": self.payment}},
        }).encode()
        signature = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
        response = APIClient().generic(
            "POST", "/api/v1/orders/webhooks/razorpay/", body,
            content_type="application/json", HTTP_X_RAZORPAY_SIGNATURE=signature,
            HTTP_X_RAZORPAY_EVENT_ID="evt_after_callback",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RazorpayPaymentEvent.objects.count(), 1)
        self.assertEqual(RazorpayPaymentEvent.objects.get().event_id, "evt_after_callback")


class PaymentConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_duplicate_capture_settles_once_on_locking_database(self):
        User = get_user_model()
        user = User.objects.create_user(email="race@example.test", password="pass")
        category = Category.objects.create(name="Race")
        product = Product.objects.create(
            name="Race Can", description="can", price=Decimal("2.00"),
            category=category, series=Product.Series.VOID, stock=6,
        )
        order = Order.objects.create(
            user=user, customer_name="Race", customer_email=user.email,
            shipping_first_name="Race", shipping_last_name="", shipping_phone="123",
            shipping_address="1 Main", shipping_city="City", shipping_state="State",
            shipping_postal_code="00000", currency="INR", subtotal_usd=Decimal("2.00"),
            exchange_rate_usd_to_inr=Decimal("83.000000"), total_inr=Decimal("166.00"),
            razorpay_order_id="order_race", inventory_deducted=True,
        )
        OrderItem.objects.create(
            order=order, product=product, product_name=product.name, quantity=2,
            unit_price_usd=Decimal("2.00"), unit_price_inr=Decimal("166.00"),
        )
        payment = {
            "id": "pay_race", "order_id": "order_race", "status": "captured",
            "amount": 16600, "currency": "INR",
        }
        barrier = threading.Barrier(2)
        outcomes, errors = [], []

        def settle():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                outcomes.append(reconcile_captured_payment(payment)[2])
            except Exception as exc:  # surfaced in the owning test thread
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=settle) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(RazorpayPaymentEvent.objects.filter(payment_id="pay_race").count(), 1)
