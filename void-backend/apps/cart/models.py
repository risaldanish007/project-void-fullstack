import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q

from ..catalog.models import Product

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null = True,
        blank= True
    )

    guest_token = models.UUIDField(
        default= uuid.uuid4,
        unique=True,
        null=True,
        blank=True,
        editable=False
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(user__isnull=False, guest_token__isnull=True)
                    | Q(user__isnull=True, guest_token__isnull=False)
                ),
                name = 'cart_has_exactly_one_owner'
            ),
        ]
    def __str__(self):
        return f'Cart {self.pk}'


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete= models.CASCADE,
        related_name="items",
    )
    product= models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("cart","product"),
                name="unique_product_per_cart",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="cart_item_quantity_at_least_one_item"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"