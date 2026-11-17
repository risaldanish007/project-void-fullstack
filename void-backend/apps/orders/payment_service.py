"""Shared, lock-protected payment and order state transitions."""
from django.db import transaction

from apps.catalog.models import Product
from apps.cart.models import Cart, CartItem
from .models import Order, RazorpayPaymentEvent


class InvalidCapturedPayment(ValueError):
    pass


class InvalidOrderTransition(ValueError):
    pass


def release_reserved_inventory_locked(order):
    """Release an order's stock once. Caller must hold the order row lock."""
    if not order.inventory_deducted:
        return False

    items = list(order.items.all())
    product_ids = sorted({item.product_id for item in items if item.product_id})
    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by("pk")
    }
    for item in items:
        product = products.get(item.product_id)
        if product:
            product.stock += item.quantity
            product.save(update_fields=["stock"])
    order.inventory_deducted = False
    return True


@transaction.atomic
def release_order_reservation(order_id, payment_status=Order.PaymentStatus.FAILED):
    """Lock an order and release its reservation, for checkout failure paths."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if (
        order.status != Order.Status.PENDING_PAYMENT
        or order.payment_status != Order.PaymentStatus.PENDING
    ):
        return order
    release_reserved_inventory_locked(order)
    order.status = Order.Status.CANCELLED
    order.payment_status = payment_status
    order.save(update_fields=["status", "payment_status", "inventory_deducted", "updated_at"])
    return order


def _locked_cart_and_items(user_id):
    """Lock cart rows before order/product rows; used by settlement/cancellation."""
    cart = Cart.objects.select_for_update().filter(user_id=user_id).first()
    if cart is None:
        return None, []
    items = list(
        CartItem.objects.select_for_update()
        .filter(cart=cart)
        .order_by("pk")
    )
    return cart, items


@transaction.atomic
def transition_order_status(order_id, new_status):
    """Apply an admin fulfillment transition or payment-aware cancellation."""
    if new_status == Order.Status.CANCELLED:
        return cancel_order(order_id)

    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == new_status:
        return order
    if order.payment_status != Order.PaymentStatus.PAID:
        raise InvalidOrderTransition("Only paid orders can enter fulfillment.")

    allowed = {
        Order.Status.PLACED: {
            Order.Status.PROCESSING, Order.Status.SHIPPED, Order.Status.DELIVERED,
        },
        Order.Status.PROCESSING: {Order.Status.SHIPPED, Order.Status.DELIVERED},
        Order.Status.SHIPPED: {Order.Status.DELIVERED},
        Order.Status.DELIVERED: set(),
        Order.Status.CANCELLED: set(),
        Order.Status.PENDING_PAYMENT: set(),
    }
    if new_status not in allowed.get(order.status, set()):
        raise InvalidOrderTransition(
            f"Cannot change order status from {order.status} to {new_status}."
        )

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order_id):
    """Cancel an unfulfilled order without losing inventory or captured funds."""
    user_id = Order.objects.filter(pk=order_id).values_list("user_id", flat=True).first()
    if user_id is None:
        raise Order.DoesNotExist

    # Global lock order for operations touching these rows:
    # Cart -> CartItem -> Order -> Product (products sorted by primary key).
    _locked_cart, _cart_items = _locked_cart_and_items(user_id)
    order = Order.objects.select_for_update().get(pk=order_id)

    if order.status == Order.Status.CANCELLED and order.payment_status not in {
        Order.PaymentStatus.PAID, Order.PaymentStatus.REFUND_PENDING,
    }:
        changed = release_reserved_inventory_locked(order)
        if changed:
            order.save(update_fields=["inventory_deducted", "updated_at"])
        return order

    unpaid_pending = (
        order.status == Order.Status.PENDING_PAYMENT
        and order.payment_status == Order.PaymentStatus.PENDING
    )
    paid_unfulfilled = (
        order.status in {
            Order.Status.PLACED, Order.Status.PROCESSING, Order.Status.CANCELLED,
        }
        and order.payment_status in {
            Order.PaymentStatus.PAID, Order.PaymentStatus.REFUND_PENDING,
        }
    )
    if not (unpaid_pending or paid_unfulfilled):
        raise InvalidOrderTransition(
            f"Order in state {order.status}/{order.payment_status} cannot be cancelled."
        )

    release_reserved_inventory_locked(order)
    order.status = Order.Status.CANCELLED

    queue_refund = False
    if paid_unfulfilled:
        if not order.razorpay_payment_id:
            raise InvalidOrderTransition("Paid order has no recorded Razorpay payment ID.")
        event = RazorpayPaymentEvent.objects.select_for_update().filter(
            payment_id=order.razorpay_payment_id,
        ).first()
        queue_refund = False
        if event and event.order_id not in (None, order.pk):
            raise InvalidOrderTransition("Payment is already associated with another order.")
        if event is None:
            event = RazorpayPaymentEvent.objects.create(
                payment_id=order.razorpay_payment_id,
                order=order,
                refund_required=True,
            )
            queue_refund = True
        else:
            queue_refund = not event.refund_required and not event.refund_processed
            event.order = order
            event.refund_required = not event.refund_processed
            event.save(update_fields=["order", "refund_required", "updated_at"])

        if event.refund_processed:
            order.payment_status = Order.PaymentStatus.REFUNDED
        else:
            order.payment_status = Order.PaymentStatus.REFUND_PENDING

    order.save(update_fields=["status", "payment_status", "inventory_deducted", "updated_at"])
    if queue_refund:
        transaction.on_commit(lambda: _queue_refund(event.pk), robust=True)
    return order


@transaction.atomic
def reconcile_captured_payment(payment, event_id=None):
    gateway_order_id = payment.get("order_id")
    payment_id = payment.get("id")
    if not gateway_order_id or not payment_id:
        raise InvalidCapturedPayment("Payment identifiers are missing.")

    order_ref = (
        Order.objects.filter(razorpay_order_id=gateway_order_id)
        .values("pk", "user_id")
        .first()
    )
    if order_ref is None:
        raise InvalidCapturedPayment("No matching order exists.")

    # Settlement follows the same cart-first hierarchy as checkout and cart writes.
    cart, cart_items = _locked_cart_and_items(order_ref["user_id"])
    order = Order.objects.select_for_update().filter(
        pk=order_ref["pk"], razorpay_order_id=gateway_order_id,
    ).first()
    if order is None:
        raise InvalidCapturedPayment("No matching order exists.")
    if (
        payment.get("status") != "captured"
        or payment.get("amount") != int(order.total_inr * 100)
        or payment.get("currency") != order.currency
    ):
        raise InvalidCapturedPayment("Payment does not match the order.")

    existing = RazorpayPaymentEvent.objects.filter(payment_id=payment_id).first()
    if existing:
        if existing.order_id not in (None, order.pk):
            raise InvalidCapturedPayment("Payment is already associated with another order.")
        if event_id and not existing.event_id:
            existing.event_id = event_id
            existing.order = order
            existing.save(update_fields=["event_id", "order", "updated_at"])
        return order, existing, False

    event = RazorpayPaymentEvent.objects.create(
        payment_id=payment_id, event_id=event_id, order=order,
    )

    # A distinct captured payment for an already-paid order must be refunded.
    if order.payment_status == Order.PaymentStatus.PAID:
        if order.razorpay_payment_id != payment_id:
            event.refund_required = True
            event.save(update_fields=["refund_required", "updated_at"])
            transaction.on_commit(lambda: _queue_refund(event.pk), robust=True)
        return order, event, False

    # A cancelled or otherwise ineligible order must never be resurrected by a
    # late callback. Persist the captured payment and let the refund task recover it.
    eligible_for_fulfillment = (
        order.status == Order.Status.PENDING_PAYMENT
        and order.payment_status == Order.PaymentStatus.PENDING
    )
    if not eligible_for_fulfillment:
        if order.status == Order.Status.CANCELLED:
            release_reserved_inventory_locked(order)
        event.refund_required = True
        event.save(update_fields=["refund_required", "updated_at"])
        order.razorpay_payment_id = payment_id
        order.payment_status = Order.PaymentStatus.REFUND_PENDING
        if order.status == Order.Status.PENDING_PAYMENT:
            order.status = Order.Status.CANCELLED
        order.save(update_fields=[
            "status", "payment_status", "razorpay_payment_id",
            "inventory_deducted", "updated_at",
        ])
        transaction.on_commit(lambda: _queue_refund(event.pk), robust=True)
        return order, event, False

    items = list(order.items.all())
    product_ids = sorted({item.product_id for item in items if item.product_id})
    products_by_id = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by("pk")
    }

    # Cleanup may have released the reservation after its gateway poll. Reacquire
    # the full quantity before confirming the order, or start a refund instead.
    if not order.inventory_deducted:
        if any(
            item.product_id is not None
            and (item.product_id not in products_by_id
                 or products_by_id[item.product_id].stock < item.quantity)
            for item in items
        ):
            event.refund_required = True
            event.save(update_fields=["refund_required", "updated_at"])
            order.payment_status = Order.PaymentStatus.REFUND_PENDING
            order.razorpay_payment_id = payment_id
            order.save(update_fields=["payment_status", "razorpay_payment_id", "updated_at"])
            transaction.on_commit(lambda: _queue_refund(event.pk), robust=True)
            return order, event, False
        for item in items:
            product = products_by_id.get(item.product_id)
            if product:
                product.stock -= item.quantity
                product.save(update_fields=["stock"])
        order.inventory_deducted = True

    order.razorpay_payment_id = payment_id
    order.payment_status = Order.PaymentStatus.PAID
    order.status = Order.Status.PLACED
    order.save(update_fields=[
        "razorpay_payment_id", "payment_status", "status",
        "inventory_deducted", "updated_at",
    ])

    # Use the cart rows already locked before the order/product rows.
    if cart:
        cart_items_by_product = {item.product_id: item for item in cart_items}
        for item in items:
            cart_item = cart_items_by_product.get(item.product_id)
            if cart_item:
                remaining = cart_item.quantity - item.quantity
                if remaining <= 0:
                    cart_item.delete()
                else:
                    cart_item.quantity = remaining
                    cart_item.save(update_fields=["quantity"])
        cart.save(update_fields=["updated_at"])
    return order, event, True


def _queue_refund(event_id):
    from .tasks import refund_captured_payment
    refund_captured_payment.delay(event_id)
