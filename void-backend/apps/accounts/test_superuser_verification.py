from django.contrib.auth import get_user_model
from django.test import TestCase
from apps.accounts.auth_views import EmailVerifiedTokenObtainPairSerializer


class SuperuserApiLoginTests(TestCase):
    def test_created_superuser_is_verified_and_can_obtain_api_tokens(self):
        User = get_user_model()
        user = User.objects.create_superuser(
            email="admin@example.test", password="Strong-test-password-123",
            is_email_verified=False,
        )
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        serializer = EmailVerifiedTokenObtainPairSerializer(data={
            "email": user.email, "password": "Strong-test-password-123",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIn("refresh", serializer.validated_data)
        self.assertIn("access", serializer.validated_data)
