from django.urls import path
from .views import CurrentCartView,CartItemDetailView,MergeGuestCartView

urlpatterns = [
    path('',CurrentCartView.as_view(), name="current-cart"),
    path("merge/", MergeGuestCartView.as_view(), name="merge-guest-cart"),
    path("items/<int:item_id>/", CartItemDetailView.as_view(), name="cart-item-detail")
]