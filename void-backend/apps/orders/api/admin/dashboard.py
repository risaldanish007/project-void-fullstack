"""
Admin dashboard statistics endpoint.
Requires IsAdminUserOrStaff permission.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminUserOrStaff
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

User = get_user_model()

LOW_STOCK_THRESHOLD = 10


class AdminDashboardView(APIView):
    """
    GET /api/v1/admin/dashboard/
    Returns aggregated statistics for the admin dashboard.
    """
    permission_classes = [IsAdminUserOrStaff]

    def get(self, request):
        # --- User stats ---
        user_stats = User.objects.aggregate(
            total_users=Count("id"),
            active_users=Count("id", filter=Q(is_active=True)),
        )

        # --- Product / inventory stats ---
        product_qs = Product.objects.all()
        total_products = product_qs.count()
        total_inventory = product_qs.aggregate(
            total=Sum("stock")
        )["total"] or 0
        low_stock_count = product_qs.filter(
            stock__gt=0, stock__lte=LOW_STOCK_THRESHOLD
        ).count()
        out_of_stock_count = product_qs.filter(stock=0).count()

        # --- Order stats ---
        order_stats = Order.objects.aggregate(
            total_orders=Count("id"),
            pending_orders=Count(
                "id",
                filter=Q(status__in=[
                    Order.Status.PLACED,
                    Order.Status.PROCESSING,
                ])
            ),
            delivered_orders=Count(
                "id",
                filter=Q(status=Order.Status.DELIVERED)
            ),
            # Sum total_inr only for PAID orders
            total_revenue_inr=Sum(
                "total_inr",
                filter=Q(payment_status=Order.PaymentStatus.PAID),
            ),
        )

        total_revenue = order_stats["total_revenue_inr"] or Decimal("0.00")

        # --- Revenue over time (last 30 days, by date) ---
        from django.utils import timezone
        import datetime

        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
        revenue_by_date = (
            Order.objects
            .filter(
                payment_status=Order.PaymentStatus.PAID,
                created_at__gte=thirty_days_ago,
            )
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(revenue=Sum("total_inr"))
            .order_by("day")
        )
        chart_data = [
            {
                "date": str(row["day"]),
                "amount": float(row["revenue"] or 0),
            }
            for row in revenue_by_date
        ]

        # --- Top selling products (by quantity in paid orders) ---
        top_sellers_qs = (
            OrderItem.objects
            .filter(order__payment_status=Order.PaymentStatus.PAID)
            .values("product_id", "product_name")
            .annotate(
                total_qty=Sum("quantity"),
                total_revenue=Sum("unit_price_inr"),
            )
            .order_by("-total_qty")[:5]
        )

        top_sellers = []
        for row in top_sellers_qs:
            product = None
            if row["product_id"]:
                try:
                    product = Product.objects.get(pk=row["product_id"])
                except Product.DoesNotExist:
                    pass
            top_sellers.append({
                "id": row["product_id"],
                "name": row["product_name"],
                "qty": row["total_qty"],
                "revenue": float(row["total_revenue"] or 0),
                "image": (
                    request.build_absolute_uri(product.image.url)
                    if product and product.image
                    else None
                ),
            })

        # --- Recent orders for bar chart ---
        recent_orders = (
            Order.objects
            .filter(payment_status=Order.PaymentStatus.PAID)
            .order_by("-created_at")[:15]
            .values("public_id", "total_inr", "created_at")
        )
        recent_payments = [
            {
                "id": str(row["public_id"])[-4:],
                "amount": float(row["total_inr"]),
                "date": str(row["created_at"].date()),
            }
            for row in reversed(list(recent_orders))
        ]

        return Response({
            # Users
            "total_users": user_stats["total_users"],
            "active_users": user_stats["active_users"],
            # Products
            "total_products": total_products,
            "total_inventory": total_inventory,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            # Orders
            "total_orders": order_stats["total_orders"],
            "pending_orders": order_stats["pending_orders"],
            "delivered_orders": order_stats["delivered_orders"],
            "total_revenue_inr": float(total_revenue),
            # Charts
            "revenue_chart": chart_data,
            "top_sellers": top_sellers,
            "recent_payments": recent_payments,
        })

