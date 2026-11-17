from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

from .models import Cart,CartItem
from ..catalog.models import Product
from .serializers import CartSerializer

from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404


class CurrentCartView(APIView):
    permission_classes = [AllowAny]

    def get_or_create_current_cart(self,request):
        if request.user.is_authenticated:
            cart,_ = Cart.objects.get_or_create(user=request.user,defaults={"guest_token":None})
            return cart,None

        guest_token = request.COOKIES.get("guest_cart")

        try:
            guest_token = UUID(guest_token) if guest_token else None
        except ValueError:
            guest_token = None

        cart = (
            Cart.objects.filter(guest_token=guest_token).first()
            if guest_token
            else None
        )

        if cart is None:
            cart = Cart.objects.create()

        return cart, str(cart.guest_token)

    def add_guest_cookie(self, response, guest_token, request):
        if guest_token is None:
            return response

        response.set_cookie(
            key="guest_cart",
            value=guest_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite=settings.COOKIE_SAMESITE,
            max_age=60 * 60 * 24 * 30,
            path="/",
            domain=settings.COOKIE_DOMAIN,
        )
        return response

    def get(self,request):
        cart, guest_token = self.get_or_create_current_cart(request)
        response = Response(
            CartSerializer(cart, context={"request": request}).data
        )
        return self.add_guest_cookie(response,guest_token,request)

    @transaction.atomic
    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity",1)

        try:
            quantity = int(quantity)
        except (TypeError,ValueError):
            return Response(
                {"quantity":"Enter a Valid whole number."},
                status = status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1 :
            return Response(
                {"quantity": "Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart, guest_token = self.get_or_create_current_cart(request)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)
        item = CartItem.objects.select_for_update().filter(
            cart=cart, product_id=product_id,
        ).first()
        product = get_object_or_404(
            Product.objects.select_for_update(),
            pk=product_id,
            is_active=True,
        )

        created = item is None
        current_quantity = item.quantity if item else 0
        new_quantity = current_quantity + quantity
        if new_quantity > product.stock:
            return Response(
                {
                    "stock": (
                        f"Only {product.stock} unit(s) of {product.name} "
                        "are currently available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if created:
            CartItem.objects.create(cart=cart, product=product, quantity=new_quantity)
        else:
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])

        cart.save(update_fields=["updated_at"])

        response = Response(
            CartSerializer(cart, context={"request": request}).data,
            status=(
                status.HTTP_200_OK
                if not created
                else status.HTTP_201_CREATED
            ),
        )

        return self.add_guest_cookie(response,guest_token,request)

class MergeGuestCartView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user_cart, _ = Cart.objects.get_or_create(
            user = request.user,
            defaults={"guest_token":None}
        )

        raw_token = request.COOKIES.get("guest_cart")

        try:
            guest_token = UUID(raw_token) if raw_token else None
        except ValueError:
            guest_token = None

        guest_cart_ref = (
            Cart.objects.filter(guest_token=guest_token).values_list("pk", flat=True).first()
            if guest_token else None
        )
        cart_ids = sorted({user_cart.pk, *([guest_cart_ref] if guest_cart_ref else [])})
        locked_carts = list(
            Cart.objects.select_for_update().filter(pk__in=cart_ids).order_by("pk")
        )
        carts_by_id = {cart.pk: cart for cart in locked_carts}
        user_cart = carts_by_id[user_cart.pk]
        guest_cart = carts_by_id.get(guest_cart_ref)

        if guest_cart:
            locked_items = list(
                CartItem.objects.select_for_update()
                .filter(cart_id__in=cart_ids)
                .order_by("pk")
            )
            guest_items = [item for item in locked_items if item.cart_id == guest_cart.pk]
            user_items_by_product = {
                item.product_id: item
                for item in locked_items
                if item.cart_id == user_cart.pk
            }
            product_ids = sorted({item.product_id for item in guest_items})
            products_by_id = {
                product.pk: product
                for product in Product.objects.select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            }

            for guest_item in guest_items:
                product = products_by_id.get(guest_item.product_id)
                if not product or not product.is_active or product.stock < 1:
                    continue

                user_item = user_items_by_product.get(product.pk)

                current_quantity = user_item.quantity if user_item else 0
                merged_quantity = min(
                    current_quantity + guest_item.quantity,
                    product.stock
                )

                if user_item:
                    user_item.quantity = merged_quantity
                    user_item.save(update_fields=["quantity"])
                elif merged_quantity:
                    created_item = CartItem.objects.create(
                        cart=user_cart,
                        product=product,
                        quantity=merged_quantity,
                    )
                    user_items_by_product[product.pk] = created_item
            guest_cart.delete()
        response = Response(
            CartSerializer(user_cart, context={"request": request}).data
        )
        if guest_cart:
            response.delete_cookie(
                "guest_cart", path="/", domain=settings.COOKIE_DOMAIN,
                samesite=settings.COOKIE_SAMESITE,
            )
        return response

class CartItemDetailView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def delete(self, request, item_id):
        cart,guest_token = CurrentCartView().get_or_create_current_cart(request)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)

        item = get_object_or_404(
            CartItem.objects.select_for_update(),
            pk=item_id,
            cart=cart
        )

        item.delete()
        cart.save(update_fields=["updated_at"])

        response = Response(
            CartSerializer(cart, context={"request": request}).data
        )
        return CurrentCartView().add_guest_cookie(
            response,
            guest_token,
            request,
        )

    @transaction.atomic
    def patch(self, request, item_id):

        cart, guest_token = CurrentCartView().get_or_create_current_cart(request)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)

        item = get_object_or_404(
            CartItem.objects.select_for_update(),
            pk=item_id,
            cart=cart
        )

        try: 
            quantity = int(request.data.get("quantity"))
        except(TypeError,ValueError):
            return Response(
                {"quantity": "Enter a valid whole number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
            {"quantity": "Quantity must be at least 1."},
            status=status.HTTP_400_BAD_REQUEST,
        )

        product = Product.objects.select_for_update().get(pk=item.product_id)
        if quantity > product.stock:
            return Response(
                {"stock": f"Only {product.stock} unit(s) are currently available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save(update_fields=["quantity"])
        cart.save(update_fields=["updated_at"])
        
        response = Response(
            CartSerializer(cart, context={"request": request}).data
        )
        return CurrentCartView().add_guest_cookie(response,guest_token,request)
