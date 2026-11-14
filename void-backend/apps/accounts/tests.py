"""
Integration tests for all admin-panel backend endpoints.

Tests cover:
  - IsAdminUserOrStaff permission (unauthenticated, customer, staff, superuser)
  - Catalog: product list, create, retrieve, update, delete
  - Orders admin: list, retrieve, status patch
  - Accounts admin: user list, retrieve, patch (ban/unban, role change)
  - Dashboard statistics endpoint
  - UserProfileSerializer exposes role / status / name correctly
"""
import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.catalog.models import Category, Ingredient, Product
from apps.orders.models import Order, OrderItem

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image():
    """Return a minimal valid JPEG as SimpleUploadedFile."""
    # 1x1 red pixel JPEG bytes
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
        b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04"
        b"\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"
        b"\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n"
        b"\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZ"
        b"cdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95"
        b"\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3"
        b"\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca"
        b"\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7"
        b"\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00\x00\x1f\xff\xd9"
    )
    return SimpleUploadedFile("test.jpg", jpeg_bytes, content_type="image/jpeg")


def _auth_header(user):
    """Return an Authorization header dict for the given user."""
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


class BaseTestCase(TestCase):
    """Creates common users and a base product for use across test classes."""

    @classmethod
    def setUpTestData(cls):
        # Three user levels
        cls.customer = User.objects.create_user(
            email="customer@void.test",
            password="pass1234!!",
            first_name="Cust",
            last_name="Omer",
            is_active=True,
        )
        cls.staff = User.objects.create_user(
            email="staff@void.test",
            password="pass1234!!",
            first_name="Staff",
            last_name="Member",
            is_active=True,
            is_staff=True,
        )
        cls.superuser = User.objects.create_superuser(
            email="super@void.test",
            password="pass1234!!",
        )

        # A product category + product
        cls.category = Category.objects.create(name="Energy")
        cls.product = Product.objects.create(
            name="VOID FLOW 01",
            description="Test description",
            price=Decimal("3.99"),
            image=_make_image(),
            category=cls.category,
            series=Product.Series.FLOW,
            stock=50,
        )
        Ingredient.objects.create(
            product=cls.product,
            name="Caffeine",
            benefit="Energy boost",
        )

        # A paid order belonging to the customer
        cls.order = Order.objects.create(
            user=cls.customer,
            customer_name="Cust Omer",
            customer_email="customer@void.test",
            shipping_first_name="Cust",
            shipping_last_name="Omer",
            shipping_phone="9999999999",
            shipping_address="123 Void St",
            shipping_city="Mumbai",
            shipping_state="MH",
            shipping_postal_code="400001",
            currency="INR",
            subtotal_usd=Decimal("3.99"),
            exchange_rate_usd_to_inr=Decimal("84.0"),
            total_inr=Decimal("335.16"),
            status=Order.Status.PLACED,
            payment_status=Order.PaymentStatus.PAID,
        )
        OrderItem.objects.create(
            order=cls.order,
            product=cls.product,
            product_name=cls.product.name,
            quantity=1,
            unit_price_usd=Decimal("3.99"),
            unit_price_inr=Decimal("335.16"),
        )


# ===========================================================================
# 1. PERMISSION CLASS
# ===========================================================================

class PermissionTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        # We'll use the admin orders list as a stable protected endpoint
        self.url = "/api/v1/orders/admin/"

    def test_unauthenticated_blocked(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_blocked(self):
        resp = self.client.get(self.url, **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_allowed(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_superuser_allowed(self):
        resp = self.client.get(self.url, **_auth_header(self.superuser))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ===========================================================================
# 2. UserProfileSerializer — role / status / name fields
# ===========================================================================

class UserProfileSerializerTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/accounts/profile/"

    def test_customer_role_in_profile(self):
        resp = self.client.get(self.url, **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["role"], "customer")
        self.assertEqual(resp.data["status"], "Active")
        self.assertEqual(resp.data["name"], "Cust Omer")

    def test_staff_role_in_profile(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["role"], "admin")

    def test_superuser_role_in_profile(self):
        resp = self.client.get(self.url, **_auth_header(self.superuser))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["role"], "admin")

    def test_inactive_user_status_banned(self):
        self.customer.is_active = False
        self.customer.save(update_fields=["is_active"])
        resp = self.client.get(self.url, **_auth_header(self.customer))
        # Inactive users cannot refresh tokens, but if they somehow hit the endpoint
        # the status field should read "Banned"
        # (DRF may return 401 if the token check includes is_active; either is fine)
        if resp.status_code == status.HTTP_200_OK:
            self.assertEqual(resp.data["status"], "Banned")
        # Restore
        self.customer.is_active = True
        self.customer.save(update_fields=["is_active"])


# ===========================================================================
# 3. CATALOG — public endpoints still work
# ===========================================================================

class CatalogPublicTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()

    def test_product_list_public(self):
        resp = self.client.get("/api/v1/catalog/products/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_product_detail_public(self):
        resp = self.client.get(f"/api/v1/catalog/products/{self.product.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "VOID FLOW 01")

    def test_product_create_requires_auth(self):
        resp = self.client.post("/api/v1/catalog/products/", {})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_product_create_requires_admin(self):
        resp = self.client.post(
            "/api/v1/catalog/products/",
            {"name": "X"},
            **_auth_header(self.customer),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ===========================================================================
# 4. CATALOG — admin CRUD
# ===========================================================================

class CatalogAdminTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()

    def test_admin_create_product(self):
        image = _make_image()
        data = {
            "name": "VOID RITE 99",
            "description": "New admin product",
            "price": "4.49",
            "stock": "20",
            "series": "RITE",
            "category": "Energy",
            "image": image,
            "ingredients[0]name": "Taurine",
            "ingredients[0]benefit": "Endurance",
        }
        resp = self.client.post(
            "/api/v1/catalog/products/",
            data,
            format="multipart",
            **_auth_header(self.staff),
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(resp.data["name"], "VOID RITE 99")

    def test_admin_update_product_price(self):
        resp = self.client.patch(
            f"/api/v1/catalog/products/{self.product.pk}/",
            {"price": "5.99", "stock": self.product.stock},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("5.99"))

    def test_admin_delete_product_with_orders_blocked(self):
        """Product referenced by an order must not be hard-deleted."""
        resp = self.client.delete(
            f"/api/v1/catalog/products/{self.product.pk}/",
            **_auth_header(self.staff),
        )
        # Must be 400 (ProtectedError) because the order references it
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", resp.data)

    def test_customer_cannot_delete_product(self):
        resp = self.client.delete(
            f"/api/v1/catalog/products/{self.product.pk}/",
            **_auth_header(self.customer),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ===========================================================================
# 5. ORDERS ADMIN
# ===========================================================================

class AdminOrderTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.list_url = "/api/v1/orders/admin/"
        self.detail_url = f"/api/v1/orders/admin/{self.order.public_id}/"

    def test_admin_list_orders(self):
        resp = self.client.get(self.list_url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [o["public_id"] for o in resp.data]
        self.assertIn(str(self.order.public_id), ids)

    def test_customer_cannot_list_all_orders(self):
        resp = self.client.get(self.list_url, **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_retrieve_order(self):
        resp = self.client.get(self.detail_url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["public_id"], str(self.order.public_id))

    def test_admin_patch_order_status_delivered(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "Delivered"},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)

    def test_admin_patch_order_status_deployed(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "Deployed"},
            format="json",
            **_auth_header(self.superuser),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)

    def test_admin_patch_order_status_cancelled(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "Cancelled"},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_admin_patch_order_invalid_status(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "flying"},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_patch_order_status(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "Delivered"},
            format="json",
            **_auth_header(self.customer),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_order_404(self):
        import uuid
        resp = self.client.get(
            f"/api/v1/orders/admin/{uuid.uuid4()}/",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# 6. USER ADMIN
# ===========================================================================

class AdminUserTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.list_url = "/api/v1/accounts/admin/users/"
        self.detail_url = f"/api/v1/accounts/admin/users/{self.customer.pk}/"

    def test_admin_list_users(self):
        resp = self.client.get(self.list_url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        emails = [u["email"] for u in resp.data]
        self.assertIn("customer@void.test", emails)

    def test_customer_blocked_from_user_list(self):
        resp = self.client.get(self.list_url, **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_retrieve_user(self):
        resp = self.client.get(self.detail_url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "customer@void.test")
        self.assertEqual(resp.data["role"], "customer")
        self.assertIn("order_count", resp.data)

    def test_admin_suspend_user(self):
        resp = self.client.patch(
            self.detail_url,
            {"is_active": False},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertEqual(resp.data["status"], "Banned")

    def test_admin_reactivate_user(self):
        self.customer.is_active = False
        self.customer.save(update_fields=["is_active"])
        resp = self.client.patch(
            self.detail_url,
            {"is_active": True},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)
        self.assertEqual(resp.data["status"], "Active")

    def test_admin_promote_user_to_staff(self):
        resp = self.client.patch(
            self.detail_url,
            {"is_staff": True},
            format="json",
            **_auth_header(self.superuser),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_staff)
        self.assertEqual(resp.data["role"], "admin")
        # Restore
        self.customer.is_staff = False
        self.customer.save(update_fields=["is_staff"])

    def test_admin_cannot_modify_self(self):
        self_url = f"/api/v1/accounts/admin/users/{self.staff.pk}/"
        resp = self.client.patch(
            self_url,
            {"is_active": False},
            format="json",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_nonexistent_user_404(self):
        resp = self.client.get(
            "/api/v1/accounts/admin/users/99999/",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_has_correct_order_count(self):
        resp = self.client.get(self.detail_url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_count"], 1)


# ===========================================================================
# 7. DASHBOARD STATISTICS
# ===========================================================================

class AdminDashboardTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/orders/admin/dashboard/"

    def test_customer_blocked(self):
        resp = self.client.get(self.url, **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_blocked(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_gets_dashboard(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_dashboard_has_required_keys(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        required = {
            "total_users", "active_users",
            "total_products", "total_inventory",
            "low_stock_count", "out_of_stock_count",
            "total_orders", "pending_orders", "delivered_orders",
            "total_revenue_inr",
            "revenue_chart", "top_sellers", "recent_payments",
        }
        for key in required:
            self.assertIn(key, resp.data, msg=f"Missing key: {key}")

    def test_dashboard_counts_are_correct(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        data = resp.data
        # We know we have at least 3 users (customer, staff, superuser)
        self.assertGreaterEqual(data["total_users"], 3)
        # At least 1 product
        self.assertGreaterEqual(data["total_products"], 1)
        # At least 1 paid order = revenue > 0
        self.assertGreater(data["total_revenue_inr"], 0)

    def test_top_sellers_has_correct_product(self):
        resp = self.client.get(self.url, **_auth_header(self.staff))
        names = [s["name"] for s in resp.data["top_sellers"]]
        self.assertIn(self.product.name, names)


# ===========================================================================
# 8. Customer-facing order endpoints still work (no regression)
# ===========================================================================

class CustomerOrderRegressionTests(BaseTestCase):

    def setUp(self):
        self.client = APIClient()

    def test_customer_can_list_own_orders(self):
        resp = self.client.get("/api/v1/orders/", **_auth_header(self.customer))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [str(o["public_id"]) for o in resp.data]
        self.assertIn(str(self.order.public_id), ids)

    def test_customer_cannot_see_other_customers_orders(self):
        # staff user has no orders; their order list must be empty
        resp = self.client.get("/api/v1/orders/", **_auth_header(self.staff))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_customer_can_retrieve_own_order(self):
        resp = self.client.get(
            f"/api/v1/orders/{self.order.public_id}/",
            **_auth_header(self.customer),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_customer_cannot_retrieve_others_order(self):
        resp = self.client.get(
            f"/api/v1/orders/{self.order.public_id}/",
            **_auth_header(self.staff),
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
