from rest_framework import serializers

from apps.orders.serializers import OrderReadSerializer


class AdminOrderReadSerializer(OrderReadSerializer):
    """Admin order representation includes the owning user's ID for lookup."""

    user = serializers.IntegerField(source="user_id", read_only=True)

    class Meta(OrderReadSerializer.Meta):
        fields = (*OrderReadSerializer.Meta.fields, "user")
