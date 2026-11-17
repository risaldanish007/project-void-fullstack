"""
Admin-only views for order management.
All endpoints require IsAdminUserOrStaff permission.
"""
import logging
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminUserOrStaff
from apps.orders.models import Order
from apps.orders.payment_service import InvalidOrderTransition, transition_order_status
from .serializers import AdminOrderReadSerializer

logger = logging.getLogger(__name__)


class AdminOrderStatusSerializer(serializers.Serializer):
    """Validates the status value supplied by an admin PATCH request."""
    STATUS_MAP = {
        # Frontend label -> Django model value
        "pending": Order.Status.PLACED,
        "placed": Order.Status.PLACED,
        "deployed": Order.Status.SHIPPED,
        "shipped": Order.Status.SHIPPED,
        "processing": Order.Status.PROCESSING,
        "delivered": Order.Status.DELIVERED,
        "cancelled": Order.Status.CANCELLED,
    }

    status = serializers.CharField()

    def validate_status(self, value):
        normalised = value.strip().lower()
        if normalised not in self.STATUS_MAP:
            valid = list(self.STATUS_MAP.keys())
            raise serializers.ValidationError(
                f"Invalid status '{value}'. Valid values: {valid}"
            )
        return self.STATUS_MAP[normalised]


class AdminOrderListView(generics.ListAPIView):
    """
    GET /api/v1/admin/orders/
    Returns all orders, newest first. Admin only.
    """
    permission_classes = [IsAdminUserOrStaff]
    serializer_class = AdminOrderReadSerializer

    def get_queryset(self):
        return (
            Order.objects
            .select_related("user")
            .prefetch_related("items")
            .order_by("-created_at")
        )


class AdminOrderDetailView(APIView):
    """
    GET  /api/v1/admin/orders/<uuid>/   – retrieve any order
    PATCH /api/v1/admin/orders/<uuid>/  – update fulfillment status
    Admin only.
    """
    permission_classes = [IsAdminUserOrStaff]

    def _get_order(self, public_id):
        try:
            return (
                Order.objects
                .select_related("user")
                .prefetch_related("items")
                .get(public_id=public_id)
            )
        except Order.DoesNotExist:
            return None

    def get(self, request, public_id):
        order = self._get_order(public_id)
        if order is None:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminOrderReadSerializer(order, context={"request": request}).data)

    def patch(self, request, public_id):
        order_id = Order.objects.filter(public_id=public_id).values_list("pk", flat=True).first()
        if order_id is None:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        try:
            order = transition_order_status(order_id, new_status)
        except InvalidOrderTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        logger.info(
            "Admin %s updated order %s status to %s",
            request.user.email, public_id, new_status,
        )

        return Response(AdminOrderReadSerializer(order, context={"request": request}).data)

