from django.core.mail import send_mail

from .otp_service import create_otp


def send_verification_email(user):
    otp = create_otp(user)

    send_mail(
        subject="Verify your VOID account",
        message=(
            f"Hello {user.email},\n\n"
            f"Your email verification OTP is: {otp}\n\n"
            "This OTP expires in 5 minutes.\n"
            "If you didn't request this, please ignore this email."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )