"""
Admin-only views for user management.
All endpoints require IsAdminUserOrStaff permission.
"""
import logging
from django.contrib.auth import get_user_model
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminUserOrStaff

User = get_user_model()
logger = logging.getLogger(__name__)


class AdminUserReadSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    order_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "name",
            "role",
            "status",
            "is_staff",
            "is_active",
            "order_count",
            "date_joined",
        )
        read_only_fields = fields

    def get_name(self, obj):
        full = f"{obj.first_name} {obj.last_name}".strip()
        return full if full else obj.email.split("@")[0]

    def get_role(self, obj):
        return "admin" if (obj.is_staff or obj.is_superuser) else "customer"

    def get_status(self, obj):
        return "Active" if obj.is_active else "Banned"

    def get_order_count(self, obj):
        return obj.orders.count()


class AdminUserPatchSerializer(serializers.Serializer):
    """Allows toggling is_active and is_staff only."""
    is_active = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)


class AdminUserListView(generics.ListAPIView):
    """
    GET /api/v1/admin/users/
    Returns all users. Admin only.
    """
    permission_classes = [IsAdminUserOrStaff]
    serializer_class = AdminUserReadSerializer

    def get_queryset(self):
        return (
            User.objects
            .prefetch_related("orders")
            .order_by("-date_joined")
        )


class AdminUserDetailView(APIView):
    """
    GET   /api/v1/admin/users/<id>/   – retrieve user
    PATCH /api/v1/admin/users/<id>/   – toggle is_active / is_staff
    Admin only. Self-demotion and self-suspension are blocked.
    """
    permission_classes = [IsAdminUserOrStaff]

    def _get_user(self, pk):
        try:
            return User.objects.prefetch_related("orders").get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self._get_user(pk)
        if user is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserReadSerializer(user, context={"request": request}).data)

    def patch(self, request, pk):
        user = self._get_user(pk)
        if user is None:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Prevent an admin from modifying their own account via this endpoint.
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot modify your own account through the admin panel."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AdminUserPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = []
        if "is_active" in data:
            user.is_active = data["is_active"]
            update_fields.append("is_active")
        if "is_staff" in data:
            user.is_staff = data["is_staff"]
            update_fields.append("is_staff")

        if update_fields:
            user.save(update_fields=update_fields)
            logger.info(
                "Admin %s modified user %s: %s",
                request.user.email, user.email, data,
            )

        return Response(AdminUserReadSerializer(user, context={"request": request}).data)

