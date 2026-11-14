from django.urls import include, path

urlpatterns = [
    path("", include("apps.accounts.api.customer.urls")),
    path("admin/", include("apps.accounts.api.admin.urls")),
]
