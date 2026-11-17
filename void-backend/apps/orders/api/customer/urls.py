from django.urls import path

from apps.orders.views import (
    CheckoutView,
    MyOrderListView,
    OrderDetailView,
    VerifyPaymentView,
    RazorpayWebhookView,
)

urlpatterns = [
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("verify-payment/", VerifyPaymentView.as_view(), name="verify-payment"),
    path("webhooks/razorpay/", RazorpayWebhookView.as_view(), name="razorpay-webhook"),
    path("", MyOrderListView.as_view(), name="my-orders"),
    path("<uuid:public_id>/", OrderDetailView.as_view(), name="order-detail"),
]
