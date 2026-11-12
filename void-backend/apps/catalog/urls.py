from django.urls import path
from .views import ProductAPI,ProductDetailsAPI
urlpatterns = [
    path('products/',ProductAPI.as_view(), name='products'),
    path('products/<int:pk>/',ProductDetailsAPI.as_view(), name='products')
]