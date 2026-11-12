from django.db import models
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    class Series(models.TextChoices):
        VOID = "VOID", "VOID"
        FLOW = "FLOW", "FLOW"
        FORM = "FORM", "FORM"
        RITE = "RITE", "RITE"

    name = models.CharField(max_length=150,unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8,decimal_places=2,validators=[MinValueValidator(0)])

    image = models.ImageField(upload_to="products/")
    image_bg = models.ImageField(
        upload_to="products/backgrounds/",
        blank=True,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    series = models.CharField(max_length=20,choices=Series.choices)
    flavor = models.CharField(max_length=100,blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="ingredients",
    )
    name = models.CharField(max_length=100)
    benefit = models.CharField(max_length=150)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product","name"],
                name="unique_ingredient_per_product",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.product.name}"