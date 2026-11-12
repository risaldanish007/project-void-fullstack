from rest_framework import serializers
from .models import Order, OrderItem

class CheckoutSerializer(serializers.Serializer):
    shipping_first_name = serializers.CharField(max_length=100)
    shipping_last_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    shipping_phone = serializers.CharField(max_length=20)
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=20)
    shipping_instructions = serializers.CharField(
        required=False,
        allow_blank=True,
    )

class PaymentVerificationSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    razorpay_order_id = serializers.CharField(max_length=100)
    razorpay_payment_id = serializers.CharField(max_length=100)
    razorpay_signature = serializers.CharField(max_length=128)

class OrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "quantity",
            "unit_price_usd",
            "unit_price_inr",
        )
        read_only_fields = fields


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "public_id",
            "customer_name",
            "customer_email",
            "shipping_first_name",
            "shipping_last_name",
            "shipping_phone",
            "shipping_address",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_instructions",
            "currency",
            "subtotal_usd",
            "exchange_rate_usd_to_inr",
            "total_inr",
            "status",
            "payment_status",
            "created_at",
            "items",
        )
        read_only_fields = fields