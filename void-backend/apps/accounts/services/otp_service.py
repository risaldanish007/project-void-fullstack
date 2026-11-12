import secrets

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from django.contrib.auth.hashers import check_password

from apps.accounts.models import EmailVerificationOTP

def generate_otp():
    otp = str(secrets.randbelow(900000)+100000)
    return  otp

def hash_otp(otp):
    return make_password(otp)

@transaction.atomic
def create_otp(user):
    otp = generate_otp()
    otp_hash = hash_otp(otp)

    EmailVerificationOTP.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)

    EmailVerificationOTP.objects.create(
        user=user,
        otp_hash=otp_hash,
        expires_at=timezone.now() + timedelta(minutes=5)
    )

    return otp
@transaction.atomic
def verify_otp(user, submitted_otp):
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
