import secrets

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model

from apps.accounts.models import EmailVerificationOTP

User = get_user_model()
MAX_OTP_EMAILS_PER_HOUR = 4
MAX_RECOVERY_EMAILS_PER_HOUR = 4

def generate_otp():
    otp = str(secrets.randbelow(900000)+100000)
    return  otp

def hash_otp(otp):
    return make_password(otp)

@transaction.atomic
def create_otp(user, only_if_unverified=False):
    # Serialize resends for a user so only one newly issued OTP remains active.
    user = User.objects.select_for_update().get(pk=user.pk)
    if only_if_unverified and (user.is_active or user.is_email_verified):
        return None

    now = timezone.now()
    if only_if_unverified and user.email_otps.filter(
        created_at__gte=now - timedelta(hours=1)
    ).count() >= MAX_OTP_EMAILS_PER_HOUR:
        return None

    if only_if_unverified and user.email_otps.filter(
        created_at__gte=now - timedelta(hours=1)
    ).count() >= MAX_RECOVERY_EMAILS_PER_HOUR:
        return None

    otp = generate_otp()
    otp_hash = hash_otp(otp)

    EmailVerificationOTP.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)

    EmailVerificationOTP.objects.create(
        user=user,
        otp_hash=otp_hash,
        expires_at=now + timedelta(minutes=5)
    )

    return otp
@transaction.atomic
def verify_otp(user, submitted_otp):
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_email_verified:
        return False, "Email is already verified."

    otp_record = (
        EmailVerificationOTP.objects
        .select_for_update()
        .filter(user=user, is_used=False)
        .order_by("-created_at")
        .first()
    )

    if not otp_record:
        return False, "No active OTP found."

    if otp_record.expires_at <= timezone.now():
        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])
        return False, "OTP has expired."

    if otp_record.attempts >= 5:
        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])
        return False, "Maximum verification attempts exceeded."

    if not check_password(submitted_otp, otp_record.otp_hash):
        otp_record.attempts += 1

        if otp_record.attempts >= 5:
            otp_record.is_used = True

        otp_record.save(update_fields=["attempts", "is_used"])

        return False, "Invalid OTP."

    # Mark OTP as used
    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])

    # Activate and verify user
    user.is_email_verified = True
    user.is_active = True
    user.save(update_fields=["is_email_verified", "is_active"])

    return True, "Email verified successfully."
