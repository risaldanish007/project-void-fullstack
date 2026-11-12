from rest_framework import serializers
from .models import Product,Category,Ingredient

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")
        read_only_fields = fields

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "benefit")
        read_only_fields = fields

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)
    image = serializers.ImageField(read_only=True)
    image_bg = serializers.ImageField(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "price",
            "image",
            "image_bg",
            "category",
            "series",
            "flavor",
            "stock",
            "is_active",
            "ingredients",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields