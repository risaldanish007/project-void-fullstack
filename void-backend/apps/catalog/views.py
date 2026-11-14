from django.db.models import ProtectedError
from rest_framework import filters, generics, status
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminUserOrStaff
from .models import Category, Ingredient, Product
from .serializer import (
    AdminProductWriteSerializer,
    CategorySerializer,
    IngredientSerializer,
    ProductSerializer,
)


class ProductAPI(generics.ListCreateAPIView):
    """
    Public GET lists products.
    Admin POST creates products.
    """
    throttle_scope = "catalog_read"
    queryset = Product.objects.select_related("category").prefetch_related("ingredients").order_by("-id")
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description", "flavor", "series"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminProductWriteSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdminUserOrStaff()]
        return []


class ProductDetailsAPI(generics.RetrieveUpdateDestroyAPIView):
    """
    Public GET retrieves a single product.
    Admin PUT/PATCH modifies a product.
    Admin DELETE removes a product.
    """
    throttle_scope = "catalog_read"
    queryset = Product.objects.select_related("category").prefetch_related("ingredients")

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return AdminProductWriteSerializer
        return ProductSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [IsAdminUserOrStaff()]
        return []

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.order_items.exists():
            return Response(
                {
                    "detail": "Cannot decommission variant because it is referenced by existing completed orders. You may mark it inactive or reduce stock to 0 instead."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {
                    "detail": "Cannot decommission variant because it is referenced by active carts or dependencies. You may mark it inactive or reduce stock to 0 instead."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
