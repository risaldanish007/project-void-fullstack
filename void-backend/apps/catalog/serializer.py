import base64
import binascii
from decimal import Decimal
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from .models import Category, Ingredient, Product


class Base64ImageField(serializers.ImageField):
    """
    Handles standard uploaded image files or base64 data URI strings.
    """
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            try:
                header, base64_str = data.split(";base64,")
                ext = header.split("/")[-1].split("+")[0]
                if ext == "jpeg":
                    ext = "jpg"
                decoded_file = base64.b64decode(base64_str)
                data = ContentFile(decoded_file, name=f"upload.{ext}")
            except (ValueError, binascii.Error) as err:
                raise serializers.ValidationError("Invalid base64 image data.") from err
        return super().to_internal_value(data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")
        read_only_fields = fields


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "benefit")
        read_only_fields = ("id",)


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


class AdminProductWriteSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=False, default="Energy")
    category_detail = CategorySerializer(source="category", read_only=True)
    ingredients = IngredientSerializer(many=True, required=False)
    image = Base64ImageField(required=False, allow_null=True)
    image_bg = Base64ImageField(required=False, allow_null=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=Decimal("0.01"))
    stock = serializers.IntegerField(min_value=0)

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
            "category_detail",
            "series",
            "flavor",
            "stock",
            "is_active",
            "ingredients",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "category_detail")

    def validate_series(self, value):
        normalized = value.upper()
        if normalized == "ZERO":
            normalized = "VOID"
        valid_series = [s[0] for s in Product.Series.choices]
        if normalized not in valid_series:
            raise serializers.ValidationError(f"Invalid series. Must be one of {valid_series}.")
        return normalized

    def validate_category(self, value):
        if isinstance(value, str):
            category, _ = Category.objects.get_or_create(name=value.strip())
            return category
        return value

    def to_representation(self, instance):
        repr_data = ProductSerializer(instance, context=self.context).data
        return repr_data

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        product = Product.objects.create(**validated_data)
        for ing in ingredients_data:
            name = ing.get("name", "").strip()
            benefit = ing.get("benefit", "").strip()
            if name:
                Ingredient.objects.create(product=product, name=name, benefit=benefit)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ing in ingredients_data:
                name = ing.get("name", "").strip()
                benefit = ing.get("benefit", "").strip()
                if name:
                    Ingredient.objects.create(product=instance, name=name, benefit=benefit)

        return instance
