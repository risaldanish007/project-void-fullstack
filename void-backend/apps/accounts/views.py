import hashlib
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle

from .serializers import (
    RegisterSerializer,
    ResendVerificationSerializer,
    UserProfileSerializer,
)
from apps.accounts.services.email_service import send_verification_email

logger = logging.getLogger(__name__)
User = get_user_model()


def verification_pending_response():
    return Response(
        {
            "detail": (
                "If this address can be verified, check your inbox. You can "
                "also request a code from the verification page."
            ),
            "verification_required": True,
        },
        status=status.HTTP_202_ACCEPTED,
    )

class RegisterView(generics.CreateAPIView):
    throttle_scope = "auth_register"
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            if user.is_active or user.is_email_verified:
                return Response(
                    {
                        "detail": "An account with this email already exists.",
                        "code": "account_already_active",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return verification_pending_response()

        try:
            with transaction.atomic():
                user = serializer.save(is_active=False, is_email_verified=False)
        except IntegrityError:
            # Another request may have created this normalized address after
            # the initial lookup. Resolve that race without creating duplicates.
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                raise
            if user.is_active or user.is_email_verified:
                return Response(
                    {
                        "detail": "An account with this email already exists.",
                        "code": "account_already_active",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return verification_pending_response()

        try:
            send_verification_email(user)
        except Exception:
            # Keep the inactive account. The customer can recover by requesting
            # a new code after email delivery is available again.
            logger.exception("Could not send the registration verification email.")

        return verification_pending_response()


class ResendEmailThrottle(SimpleRateThrottle):
    scope = "auth_resend_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email")
        if not isinstance(email, str) or not email.strip():
            return None

        digest = hashlib.sha256(email.strip().casefold().encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class ResendIPThrottle(AnonRateThrottle):
    scope = "auth_resend_ip"


class ResendOTPView(generics.GenericAPIView):
    serializer_class = ResendVerificationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ResendIPThrottle, ResendEmailThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user and not user.is_active and not user.is_email_verified:
            try:
                send_verification_email(user, only_if_unverified=True)
            except Exception:
                # Keep responses generic and leave the account recoverable.
                logger.exception("Could not send a registration recovery email.")

        return Response(
            {
                "detail": (
                    "If an unverified account can receive a code, check your "
                    "inbox shortly. If nothing arrives, try again later."
                )
            },
            status=status.HTTP_200_OK,
        )

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
