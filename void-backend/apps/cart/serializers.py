from rest_framework import serializers
from apps.catalog.serializer import ProductSerializer
from .models import Cart,CartItem

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only = True)
    total_item_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "product", "quantity", "total_item_price")
        read_only_fields = fields

    def get_total_item_price(self, cart_item):
        return cart_item.product.price * cart_item.quantity

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True,read_only=True)
    total_quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_quantity", "total_price")
        read_only_fields = fields

    def get_total_quantity(self, cart):
        return sum(item.quantity for item in cart.items.all())

    def get_total_price(self, cart):
        return sum(
            item.product.price * item.quantity
            for item in cart.items.select_related("product").all()
        )
