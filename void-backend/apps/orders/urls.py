from django.urls import include, path

urlpatterns = [
    path("", include("apps.orders.api.customer.urls")),
    path("admin/", include("apps.orders.api.admin.urls")),
]
