import logging
import razorpay
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404

from razorpay.errors import SignatureVerificationError
from rest_framework import status,generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart, CartItem
from .models import Order, OrderItem
from .serializers import CheckoutSerializer, PaymentVerificationSerializer, OrderReadSerializer


logger = logging.getLogger(__name__)
TWO_PLACES = Decimal("0.01")


class CheckoutView(APIView):
    throttle_scope = "order_checkout"
    permission_classes = [IsAuthenticated]

    @transaction.atomic
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

        cart = (
            Cart.objects.select_for_update()
            .filter(user=request.user)
            .first()
        )

        if cart is None:
            return Response(
                {"detail": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items = list(
            cart.items.select_for_update()
            .select_related("product")
            .order_by("id")
        )

        if not cart_items:
            return Response(
                {"detail": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check every item before reserving any stock.
        for item in cart_items:
            if not item.product.is_active:
                return Response(
                    {"detail": f"{item.product.name} is no longer available."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if item.quantity > item.product.stock:
                return Response(
                    {
                        "detail": (
                            f"Only {item.product.stock} unit(s) of "
                            f"{item.product.name} are currently available."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        subtotal_usd = sum(
            (item.product.price * item.quantity for item in cart_items),
            Decimal("0.00"),
        )

        order = Order.objects.create(
            user=request.user,
            customer_name=(
                f"{shipping['shipping_first_name']} "
                f"{shipping.get('shipping_last_name', '')}"
            ).strip(),
            customer_email=request.user.email,
            shipping_first_name=shipping["shipping_first_name"],
            shipping_last_name=shipping.get("shipping_last_name", ""),
            shipping_phone=shipping["shipping_phone"],
            shipping_address=shipping["shipping_address"],
            shipping_city=shipping["shipping_city"],
            shipping_state=shipping["shipping_state"],
            shipping_postal_code=shipping["shipping_postal_code"],
            shipping_instructions=shipping.get("shipping_instructions", ""),
            currency="INR",
            subtotal_usd=subtotal_usd,
            exchange_rate_usd_to_inr=exchange_rate,
            total_inr=Decimal("0.00"),
        )

        total_inr = Decimal("0.00")

        for item in cart_items:
            product = item.product

            unit_price_inr = (product.price * exchange_rate).quantize(
                TWO_PLACES,
                rounding=ROUND_HALF_UP,
            )
            total_inr += unit_price_inr * item.quantity

            # Reserve the units by reducing the available stock.
            product.stock -= item.quantity
            product.save(update_fields=["stock"])

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=item.quantity,
                unit_price_usd=product.price,
                unit_price_inr=unit_price_inr,
            )

        order.total_inr = total_inr.quantize(
            TWO_PLACES,
            rounding=ROUND_HALF_UP,
        )
        order.inventory_deducted = True
        order.save(update_fields=[
            "total_inr",
            "inventory_deducted",
            "updated_at",
        ])

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
            # This also rolls back the stock reservation.
            transaction.set_rollback(True)
            return Response(
                {"detail": "Could not start payment right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

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


class VerifyPaymentView(APIView):
    throttle_scope = "payment_verify"
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        order = get_object_or_404(
            Order.objects.select_for_update(),
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

            return Response(
                {"detail": "This order has already been paid."},
                status=status.HTTP_409_CONFLICT,
            )

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

        order.razorpay_payment_id = data["razorpay_payment_id"]
        order.payment_status = Order.PaymentStatus.PAID
        order.status = Order.Status.PLACED
        order.save(update_fields=[
            "razorpay_payment_id",
            "payment_status",
            "status",
            "updated_at",
        ])

        # Remove only the quantities in this order, preserving any newer
        # cart items the user may have added while payment was in progress.
        cart = (
            Cart.objects.select_for_update()
            .filter(user=request.user)
            .first()
        )

        if cart:
            for order_item in order.items.all():
                if order_item.product_id is None:
                    continue

                cart_item = (
                    CartItem.objects.select_for_update()
                    .filter(
                        cart=cart,
                        product_id=order_item.product_id,
                    )
                    .first()
                )

                if cart_item is None:
                    continue

                remaining_quantity = cart_item.quantity - order_item.quantity

                if remaining_quantity <= 0:
                    cart_item.delete()
                else:
                    cart_item.quantity = remaining_quantity
                    cart_item.save(update_fields=["quantity"])

            cart.save(update_fields=["updated_at"])

        return Response({
            "order_id": str(order.public_id),
            "status": order.status,
            "payment_status": order.payment_status,
        })

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