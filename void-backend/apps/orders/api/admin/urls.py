from django.urls import path

from .dashboard import AdminDashboardView
from .views import AdminOrderDetailView, AdminOrderListView

urlpatterns = [
    path("", AdminOrderListView.as_view(), name="admin-order-list"),
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("<uuid:public_id>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
]
