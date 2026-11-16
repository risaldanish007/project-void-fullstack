import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import EmailVerificationOTP
from apps.accounts.services.email_service import send_verification_email

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationRecoveryTests(TestCase):
    register_url = "/api/v1/accounts/register/"
    resend_url = "/api/v1/accounts/resend-otp/"
    verify_url = "/api/v1/accounts/verify-email/"

    def setUp(self):
        self.client = APIClient()
        cache.clear()
        if hasattr(mail, "outbox"):
            mail.outbox.clear()

    def tearDown(self):
        cache.clear()

    def registration_payload(self, email="new-customer@example.test"):
        return {
            "email": email,
            "first_name": "Avery",
            "last_name": "Customer",
            "password": "Void!Passphrase842",
        }

    def latest_email_otp(self):
        match = re.search(r"OTP is: (\d{6})", mail.outbox[-1].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_registration_creates_inactive_account_and_sends_hashed_otp(self):
        response = self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )

        self.assertEqual(response.status_code, 202)
        user = User.objects.get(email="new-customer@example.test")
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        record = EmailVerificationOTP.objects.get(user=user)
        self.assertNotIn(self.latest_email_otp(), record.otp_hash)
        self.assertNotIn("otp", response.data)

    def test_duplicate_inactive_registration_returns_recovery_response(self):
        self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )
        first_response = self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(User.objects.filter(email="new-customer@example.test").count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        resend_response = self.client.post(
            self.resend_url,
            {"email": " NEW-CUSTOMER@EXAMPLE.TEST "},
            format="json",
        )
        self.assertEqual(resend_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_active_duplicate_is_rejected_without_changing_account(self):
        user = User.objects.create_user(
            email="active@example.test",
            password="Void!Passphrase842",
            is_active=True,
            is_email_verified=True,
        )

        response = self.client.post(
            self.register_url,
            self.registration_payload("ACTIVE@EXAMPLE.TEST"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "account_already_active")
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertEqual(len(mail.outbox), 0)

    def test_successful_verification_activates_account_and_code_cannot_be_reused(self):
        self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )
        otp = self.latest_email_otp()

        response = self.client.post(
            self.verify_url,
            {"email": "NEW-CUSTOMER@example.test", "otp": otp},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="new-customer@example.test")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_email_verified)
        self.assertTrue(
            EmailVerificationOTP.objects.get(user=user).is_used
        )
        replay = self.client.post(
            self.verify_url,
            {"email": user.email, "otp": otp},
            format="json",
        )
        self.assertEqual(replay.status_code, 400)

    def test_resend_invalidates_old_otp_and_only_latest_verifies(self):
        with patch(
            "apps.accounts.services.otp_service.generate_otp",
            side_effect=["123456", "654321"],
        ):
            self.client.post(
                self.register_url, self.registration_payload(), format="json"
            )
            old_otp = self.latest_email_otp()
            resend = self.client.post(
                self.resend_url,
                {"email": "new-customer@example.test"},
                format="json",
            )
            new_otp = self.latest_email_otp()

        self.assertEqual(resend.status_code, 200)
        self.assertNotEqual(old_otp, new_otp)
        self.assertEqual(
            EmailVerificationOTP.objects.filter(is_used=False).count(), 1
        )
        old_attempt = self.client.post(
            self.verify_url,
            {"email": "new-customer@example.test", "otp": old_otp},
            format="json",
        )
        self.assertEqual(old_attempt.status_code, 400)
        latest_attempt = self.client.post(
            self.verify_url,
            {"email": "new-customer@example.test", "otp": new_otp},
            format="json",
        )
        self.assertEqual(latest_attempt.status_code, 200)

    def test_expired_and_invalid_otps_are_rejected(self):
        self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )
        user = User.objects.get(email="new-customer@example.test")
        record = EmailVerificationOTP.objects.get(user=user)
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=["expires_at"])

        expired = self.client.post(
            self.verify_url,
            {"email": user.email, "otp": self.latest_email_otp()},
            format="json",
        )
        self.assertEqual(expired.status_code, 400)

        self.client.post(
            self.register_url,
            self.registration_payload("another-customer@example.test"),
            format="json",
        )
        invalid = self.client.post(
            self.verify_url,
            {"email": "another-customer@example.test", "otp": "000000"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(
            User.objects.get(email="another-customer@example.test").is_active
        )

    def test_resend_is_generic_for_unknown_and_active_emails(self):
        User.objects.create_user(
            email="verified@example.test",
            password="Void!Passphrase842",
            is_active=True,
            is_email_verified=True,
        )

        unknown = self.client.post(
            self.resend_url, {"email": "unknown@example.test"}, format="json"
        )
        verified = self.client.post(
            self.resend_url, {"email": "verified@example.test"}, format="json"
        )

        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.data, verified.data)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(EmailVerificationOTP.objects.count(), 0)

    def test_email_delivery_failure_keeps_account_recoverable(self):
        with patch(
            "apps.accounts.services.email_service.send_mail",
            side_effect=OSError("mail provider unavailable"),
        ):
            response = self.client.post(
                self.register_url, self.registration_payload(), format="json"
            )

        self.assertEqual(response.status_code, 202)
        user = User.objects.get(email="new-customer@example.test")
        self.assertFalse(user.is_active)

        recovered = self.client.post(
            self.resend_url,
            {"email": user.email},
            format="json",
        )
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(EmailVerificationOTP.objects.filter(user=user).count(), 2)

    def test_resend_is_throttled_per_email(self):
        responses = [
            self.client.post(
                self.resend_url,
                {"email": "unknown@example.test"},
                format="json",
            )
            for _ in range(4)
        ]

        self.assertEqual([response.status_code for response in responses], [200, 200, 200, 429])

    def test_otp_history_caps_email_delivery_across_cache_restarts(self):
        self.client.post(
            self.register_url, self.registration_payload(), format="json"
        )
        user = User.objects.get(email="new-customer@example.test")

        for _ in range(3):
            self.assertTrue(
                send_verification_email(user, only_if_unverified=True)
            )

        self.assertFalse(send_verification_email(user, only_if_unverified=True))
        self.assertEqual(EmailVerificationOTP.objects.filter(user=user).count(), 4)
        self.assertEqual(len(mail.outbox), 4)

