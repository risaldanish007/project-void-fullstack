import threading
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, RazorpayPaymentEvent
from apps.orders.payment_service import (
    reconcile_captured_payment,
    release_order_reservation,
)


class AdminOrderCancellationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="cancel-buyer@example.test", password="pass")
        self.staff = User.objects.create_user(
            email="cancel-staff@example.test", password="pass", is_staff=True,
        )
        self.category = Category.objects.create(name="Cancellation")
        # Six are available after reserving two units from an initial stock of eight.
        self.product = Product.objects.create(
            name="Cancellation Can", description="can", price=Decimal("2.00"),
            category=self.category, series=Product.Series.VOID, stock=6,
        )
        self.order = Order.objects.create(
            user=self.user, customer_name="Buyer", customer_email=self.user.email,
            shipping_first_name="Buyer", shipping_last_name="", shipping_phone="123",
            shipping_address="1 Main", shipping_city="City", shipping_state="State",
            shipping_postal_code="00000", currency="INR", subtotal_usd=Decimal("4.00"),
            exchange_rate_usd_to_inr=Decimal("83.000000"), total_inr=Decimal("332.00"),
            razorpay_order_id="order_cancel", inventory_deducted=True,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name=self.product.name,
            quantity=2, unit_price_usd=Decimal("2.00"), unit_price_inr=Decimal("166.00"),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.staff)
        self.url = f"/api/v1/orders/admin/{self.order.public_id}/"

    def cancel_via_admin(self):
        return self.client.patch(self.url, {"status": "cancelled"}, format="json")

    def test_cancelling_pending_order_releases_inventory_once(self):
        first = self.cancel_via_admin()
        second = self.cancel_via_admin()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.PENDING)
        self.assertFalse(self.order.inventory_deducted)
        self.assertEqual(self.product.stock, 8)
        self.assertFalse(RazorpayPaymentEvent.objects.exists())

    def test_cancelling_paid_order_records_refund_and_releases_stock(self):
        self.order.status = Order.Status.PLACED
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.razorpay_payment_id = "pay_cancel"
        self.order.save(update_fields=["status", "payment_status", "razorpay_payment_id"])
        event = RazorpayPaymentEvent.objects.create(
            payment_id="pay_cancel", order=self.order,
        )

        with patch("apps.orders.payment_service._queue_refund") as queue_refund:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.cancel_via_admin()
                self.assertEqual(response.status_code, 200)
            queue_refund.assert_called_once_with(event.pk)

        self.order.refresh_from_db()
        self.product.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.REFUND_PENDING)
        self.assertFalse(self.order.inventory_deducted)
        self.assertEqual(self.product.stock, 8)
        self.assertTrue(event.refund_required)
        self.assertEqual(RazorpayPaymentEvent.objects.filter(payment_id="pay_cancel").count(), 1)

    def test_repeated_paid_cancellation_is_idempotent(self):
        self.order.status = Order.Status.PLACED
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.razorpay_payment_id = "pay_cancel_repeat"
        self.order.save(update_fields=["status", "payment_status", "razorpay_payment_id"])
        event = RazorpayPaymentEvent.objects.create(
            payment_id="pay_cancel_repeat", order=self.order,
        )
        with patch("apps.orders.payment_service._queue_refund") as queue_refund:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.cancel_via_admin().status_code, 200)
                self.assertEqual(self.cancel_via_admin().status_code, 200)
            queue_refund.assert_called_once_with(event.pk)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(RazorpayPaymentEvent.objects.filter(payment_id=event.payment_id).count(), 1)

    def test_invalid_fulfillment_transition_is_rejected(self):
        response = self.client.patch(self.url, {"status": "delivered"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(self.product.stock, 6)

    def test_paid_order_without_payment_id_cannot_be_cancelled(self):
        self.order.status = Order.Status.PLACED
        self.order.payment_status = Order.PaymentStatus.PAID
        self.order.save(update_fields=["status", "payment_status"])
        response = self.cancel_via_admin()
        self.assertEqual(response.status_code, 409)
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PLACED)
        self.assertTrue(self.order.inventory_deducted)
        self.assertEqual(self.product.stock, 6)

    def test_late_capture_after_cancellation_stays_cancelled_and_queues_refund(self):
        payment = {
            "id": "pay_late_cancel", "order_id": "order_cancel", "status": "captured",
            "amount": 33200, "currency": "INR",
        }
        with patch("apps.orders.payment_service._queue_refund") as queue_refund:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.cancel_via_admin().status_code, 200)
                result, event, settled = reconcile_captured_payment(payment)
                self.assertFalse(settled)
                self.assertEqual(result.status, Order.Status.CANCELLED)
            self.assertEqual(queue_refund.call_count, 1)

        self.order.refresh_from_db()
        self.product.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.order.payment_status, Order.PaymentStatus.REFUND_PENDING)
        self.assertFalse(self.order.inventory_deducted)
        self.assertEqual(self.product.stock, 8)
        self.assertTrue(event.refund_required)


class OrderInventoryConcurrencyTests(TransactionTestCase):
    """These tests run only on a backend with real select_for_update support."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="race-buyer@example.test", password="pass")
        self.category = Category.objects.create(name="Concurrency")
        self.product = Product.objects.create(
            name="Concurrency Can", description="can", price=Decimal("2.00"),
            category=self.category, series=Product.Series.VOID, stock=10,
        )
        self.cart = Cart.objects.create(user=self.user, guest_token=None)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    @staticmethod
    def run_together(*operations):
        barrier = threading.Barrier(len(operations))
        errors = []

        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                operation()
            except Exception as exc:
                errors.append(exc)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=run, args=(operation,)) for operation in operations]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=25)
        return threads, errors

    @skipUnlessDBFeature("has_select_for_update")
    def test_checkout_and_cart_addition_keep_stock_and_cart_consistent(self):
        from django.test import override_settings

        payload = {
            "shipping_first_name": "Buyer", "shipping_last_name": "",
            "shipping_phone": "123", "shipping_address": "1 Main",
            "shipping_city": "City", "shipping_state": "State",
            "shipping_postal_code": "00000",
        }
        class FakeRazorpayClient:
            @property
            def order(self):
                return self

            def create(self, data):
                return {"id": "order_checkout_race"}

        def checkout():
            client = APIClient()
            client.force_authenticate(self.user)
            with override_settings(USD_TO_INR_RATE="83", RAZORPAY_KEY_ID="key", RAZORPAY_KEY_SECRET="secret"):
                response = client.post("/api/v1/orders/checkout/", payload, format="json")
                if response.status_code != 201:
                    raise AssertionError(f"checkout returned {response.status_code}: {response.data}")

        def add_to_cart():
            client = APIClient()
            client.force_authenticate(self.user)
            response = client.post(
                "/api/v1/cart/", {"product_id": self.product.pk, "quantity": 1}, format="json",
            )
            if response.status_code not in (200, 201):
                raise AssertionError(f"cart add returned {response.status_code}: {response.data}")

        with patch("apps.orders.views.razorpay.Client", return_value=FakeRazorpayClient()):
            threads, errors = self.run_together(checkout, add_to_cart)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.product.refresh_from_db()
        self.cart_item.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)
        self.assertEqual(self.cart_item.quantity, 2)
        order = Order.objects.get(user=self.user)
        self.assertIn(order.items.get().quantity, (1, 2))

    @skipUnlessDBFeature("has_select_for_update")
    def test_checkout_and_settlement_follow_cart_first_lock_order(self):
        from django.test import override_settings

        self.product.stock = 8
        self.product.save(update_fields=["stock"])
        previous_order = Order.objects.create(
            user=self.user, customer_name="Buyer", customer_email=self.user.email,
            shipping_first_name="Buyer", shipping_last_name="", shipping_phone="123",
            shipping_address="1 Main", shipping_city="City", shipping_state="State",
            shipping_postal_code="00000", currency="INR", subtotal_usd=Decimal("2.00"),
            exchange_rate_usd_to_inr=Decimal("83.000000"), total_inr=Decimal("166.00"),
            razorpay_order_id="order_previous", inventory_deducted=True,
        )
        OrderItem.objects.create(
            order=previous_order, product=self.product, product_name=self.product.name,
            quantity=1, unit_price_usd=Decimal("2.00"), unit_price_inr=Decimal("166.00"),
        )
        payment = {
            "id": "pay_previous", "order_id": "order_previous", "status": "captured",
            "amount": 16600, "currency": "INR",
        }
        payload = {
            "shipping_first_name": "Buyer", "shipping_last_name": "",
            "shipping_phone": "123", "shipping_address": "1 Main",
            "shipping_city": "City", "shipping_state": "State",
            "shipping_postal_code": "00000",
        }
        class FakeRazorpayClient:
            @property
            def order(self):
                return self

            def create(self, data):
                return {"id": "order_checkout_after_previous"}

        def checkout():
            client = APIClient()
            client.force_authenticate(self.user)
            with override_settings(USD_TO_INR_RATE="83", RAZORPAY_KEY_ID="key", RAZORPAY_KEY_SECRET="secret"):
                response = client.post("/api/v1/orders/checkout/", payload, format="json")
                if response.status_code not in (201, 400):
                    raise AssertionError(f"checkout returned {response.status_code}: {response.data}")

        def settle():
            reconcile_captured_payment(payment)

        with patch("apps.orders.views.razorpay.Client", return_value=FakeRazorpayClient()):
            threads, errors = self.run_together(checkout, settle)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.product.refresh_from_db()
        self.cart.refresh_from_db()
        self.assertIn(self.product.stock, (7, 8))
        self.assertLessEqual(
            Order.objects.filter(user=self.user, status=Order.Status.PENDING_PAYMENT).count(), 1,
        )

    @skipUnlessDBFeature("has_select_for_update")
    def test_settlement_racing_reservation_release_never_releases_twice(self):
        order = Order.objects.create(
            user=self.user, customer_name="Buyer", customer_email=self.user.email,
            shipping_first_name="Buyer", shipping_last_name="", shipping_phone="123",
            shipping_address="1 Main", shipping_city="City", shipping_state="State",
            shipping_postal_code="00000", currency="INR", subtotal_usd=Decimal("2.00"),
            exchange_rate_usd_to_inr=Decimal("83.000000"), total_inr=Decimal("166.00"),
            razorpay_order_id="order_release_race", inventory_deducted=True,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            quantity=2, unit_price_usd=Decimal("2.00"), unit_price_inr=Decimal("166.00"),
        )
        payment = {
            "id": "pay_release_race", "order_id": "order_release_race", "status": "captured",
            "amount": 16600, "currency": "INR",
        }

        with patch("apps.orders.payment_service._queue_refund"):
            threads, errors = self.run_together(
                lambda: release_order_reservation(order.pk),
                lambda: reconcile_captured_payment(payment),
            )
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertGreaterEqual(self.product.stock, 0)
        if order.payment_status == Order.PaymentStatus.PAID:
            self.assertTrue(order.inventory_deducted)
            self.assertEqual(self.product.stock, 10)
        else:
            self.assertFalse(order.inventory_deducted)
            self.assertEqual(self.product.stock, 12)
            self.assertEqual(order.payment_status, Order.PaymentStatus.REFUND_PENDING)
