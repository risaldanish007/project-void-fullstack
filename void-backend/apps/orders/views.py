import logging
import hashlib
import hmac
import json
import razorpay
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from razorpay.errors import SignatureVerificationError
from rest_framework import status,generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.catalog.models import Product
from .models import Order, OrderItem, RazorpayPaymentEvent, RazorpayWebhookReceipt
from .payment_service import (
    reconcile_captured_payment,
    release_order_reservation,
    InvalidCapturedPayment,
)
from .serializers import CheckoutSerializer, PaymentVerificationSerializer, OrderReadSerializer


logger = logging.getLogger(__name__)
TWO_PLACES = Decimal("0.01")


class CheckoutView(APIView):
    throttle_scope = "order_checkout"
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shipping = serializer.validated_data

        try:
            exchange_rate = Decimal(settings.USD_TO_INR_RATE)
        except (AttributeError, TypeError, ValueError):
            return Response(
                {"detail": "The USD to INR exchange rate is not configured correctly."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if exchange_rate <= 0:
            return Response(
                {"detail": "The USD to INR exchange rate must be greater than zero."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=request.user).first()
            if cart is None:
                return Response({"detail": "Your cart is empty."}, status=400)
            cart_items = list(cart.items.select_for_update().order_by("id"))
            if not cart_items:
                return Response({"detail": "Your cart is empty."}, status=400)
            products = {
                p.pk: p for p in Product.objects.select_for_update()
                .filter(pk__in=sorted({i.product_id for i in cart_items}))
                .order_by("pk")
            }
            for item in cart_items:
                product = products.get(item.product_id)
                if not product or not product.is_active:
                    return Response({"detail": "A cart product is no longer available."}, status=400)
                if item.quantity > product.stock:
                    return Response({"detail": f"Only {product.stock} unit(s) of {product.name} are currently available."}, status=400)

            subtotal_usd = sum((products[i.product_id].price * i.quantity for i in cart_items), Decimal("0.00"))
            order = Order.objects.create(
                user=request.user,
                customer_name=f"{shipping['shipping_first_name']} {shipping.get('shipping_last_name', '')}".strip(),
                customer_email=request.user.email,
                shipping_first_name=shipping["shipping_first_name"],
                shipping_last_name=shipping.get("shipping_last_name", ""),
                shipping_phone=shipping["shipping_phone"],
                shipping_address=shipping["shipping_address"],
                shipping_city=shipping["shipping_city"],
                shipping_state=shipping["shipping_state"],
                shipping_postal_code=shipping["shipping_postal_code"],
                shipping_instructions=shipping.get("shipping_instructions", ""),
                currency="INR", subtotal_usd=subtotal_usd,
                exchange_rate_usd_to_inr=exchange_rate, total_inr=Decimal("0.00"),
            )
            total_inr = Decimal("0.00")
            for item in cart_items:
                product = products[item.product_id]
                unit_price_inr = (product.price * exchange_rate).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                total_inr += unit_price_inr * item.quantity
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
                OrderItem.objects.create(
                    order=order, product=product, product_name=product.name,
                    quantity=item.quantity, unit_price_usd=product.price,
                    unit_price_inr=unit_price_inr,
                )
            order.total_inr = total_inr.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            order.inventory_deducted = True
            order.save(update_fields=["total_inr", "inventory_deducted", "updated_at"])
            amount_paise = int(order.total_inr * 100)

        try:
            razorpay_client = razorpay.Client(
                auth=(
                    settings.RAZORPAY_KEY_ID,
                    settings.RAZORPAY_KEY_SECRET,
                )
            )

            razorpay_order = razorpay_client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": str(order.public_id),
                    "notes": {
                        "void_order_id": str(order.public_id),
                    },
                }
            )
        except Exception:
            logger.exception(
                "Razorpay order creation failed for order %s",
                order.public_id,
            )
            self._release_reservation(order.pk, Order.PaymentStatus.FAILED)
            return Response(
                {"detail": "Could not start payment right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order.pk)
            order.razorpay_order_id = razorpay_order["id"]
            order.save(update_fields=["razorpay_order_id", "updated_at"])

        return Response(
            {
                "order_id": str(order.public_id),
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "razorpay_order_id": order.razorpay_order_id,
                "amount": amount_paise,
                "currency": "INR",
                "subtotal_usd": str(order.subtotal_usd),
                "exchange_rate_usd_to_inr": str(
                    order.exchange_rate_usd_to_inr
                ),
                "total_inr": str(order.total_inr),
                "status": order.status,
                "payment_status": order.payment_status,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _release_reservation(order_id, payment_status):
        return release_order_reservation(order_id, payment_status)


class VerifyPaymentView(APIView):
    throttle_scope = "payment_verify"
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = get_object_or_404(
            Order.objects,
            public_id=data["order_id"],
            user=request.user,
        )

        # Make retries safe: don't process stock or cart changes twice.
        if order.payment_status == Order.PaymentStatus.PAID:
            if order.razorpay_payment_id == data["razorpay_payment_id"]:
                return Response({
                    "order_id": str(order.public_id),
                    "status": order.status,
                    "payment_status": order.payment_status,
                })

        if data["razorpay_order_id"] != order.razorpay_order_id:
            return Response(
                {"detail": "Razorpay order does not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        razorpay_client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })
        except SignatureVerificationError:
            return Response(
                {"detail": "Payment signature is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = razorpay_client.payment.fetch(
                data["razorpay_payment_id"]
            )
        except Exception:
            logger.exception(
                "Could not fetch Razorpay payment for order %s",
                order.public_id,
            )
            return Response(
                {"detail": "Could not confirm payment status right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        expected_amount_paise = int(order.total_inr * 100)

        if (
            payment.get("order_id") != order.razorpay_order_id
            or payment.get("amount") != expected_amount_paise
            or payment.get("currency") != "INR"
        ):
            return Response(
                {"detail": "Payment details do not match this order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.get("status") != "captured":
            return Response(
                {"detail": "Payment has not been captured yet."},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            order, _, settled = reconcile_captured_payment(payment)
        except InvalidCapturedPayment:
            return Response({"detail": "Payment details do not match this order."}, status=400)
        if not settled:
            return Response({"detail": "Payment received; refund processing is required."}, status=409)

        return Response({
            "order_id": str(order.public_id),
            "status": order.status,
            "payment_status": order.payment_status,
        })


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        body = request.body
        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature):
            return Response({"detail": "Invalid webhook signature."}, status=400)
        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return Response({"detail": "Invalid webhook body."}, status=400)
        if not isinstance(payload, dict):
            return Response({"detail": "Invalid webhook body."}, status=400)

        event_name = payload.get("event")
        event_id = request.headers.get("X-Razorpay-Event-Id", "")
        if not event_id:
            return Response({"detail": "Missing event identifier."}, status=400)
        if RazorpayWebhookReceipt.objects.filter(event_id=event_id).exists():
            return Response({"received": True})
        payment_id = ""
        ignored = False
        try:
            with transaction.atomic():
                RazorpayWebhookReceipt.objects.create(
                    event_id=event_id, event_type=str(event_name or "")[:80],
                )
                if event_name == "payment.captured":
                    try:
                        payment = payload["payload"]["payment"]["entity"]
                        payment_id = str(payment.get("id", ""))
                        reconcile_captured_payment(payment, event_id)
                    except (KeyError, TypeError, InvalidCapturedPayment) as exc:
                        ignored = True
                        logger.warning("Ignored invalid Razorpay capture event %s: %s", event_id, exc)
                elif event_name == "refund.processed":
                    refund = payload.get("payload", {}).get("refund", {}).get("entity", {})
                    payment_id = str(refund.get("payment_id", ""))
                    event = RazorpayPaymentEvent.objects.filter(
                        payment_id=payment_id, refund_id=refund.get("id"),
                    ).first()
                    if event:
                        if event.order_id:
                            Order.objects.select_for_update().filter(pk=event.order_id).first()
                        event = RazorpayPaymentEvent.objects.select_for_update().get(pk=event.pk)
                        event.refund_processed = True
                        event.refund_required = False
                        event.save(update_fields=["refund_processed", "refund_required", "updated_at"])
                        if event.order_id:
                            order = Order.objects.get(pk=event.order_id)
                            if order.payment_status == Order.PaymentStatus.REFUND_PENDING and order.razorpay_payment_id == payment_id:
                                order.payment_status = Order.PaymentStatus.REFUNDED
                                order.save(update_fields=["payment_status", "updated_at"])
                receipt = RazorpayWebhookReceipt.objects.select_for_update().get(event_id=event_id)
                receipt.payment_id = payment_id
                receipt.save(update_fields=["payment_id"])
        except IntegrityError:
            # A concurrent retry may have inserted this event ID first.
            if RazorpayWebhookReceipt.objects.filter(event_id=event_id).exists():
                return Response({"received": True})
            raise
        return Response({"received": True, **({"ignored": True} if ignored else {})})

class MyOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderReadSerializer

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderReadSerializer
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items")
        )
