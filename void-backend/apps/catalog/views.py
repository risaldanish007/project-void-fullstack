from rest_framework import generics
from .serializer import ProductSerializer,CategorySerializer,IngredientSerializer
from .models import Product,Category,Ingredient
from rest_framework import filters, generics

class ProductAPI(generics.ListAPIView):
    throttle_scope = "catalog_read"
    queryset = Product.objects.select_related("category").prefetch_related("ingredients")
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description", "flavor", "series"]

class ProductDetailsAPI(generics.RetrieveAPIView):
    throttle_scope = "catalog_read"
    queryset = Product.objects.select_related("category").prefetch_related("ingredients")
    serializer_class = ProductSerializer
