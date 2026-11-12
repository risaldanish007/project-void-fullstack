from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.contrib.auth import get_user_model

from rest_framework import status,generics,serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import EmailVerificationSerializer, UserProfileSerializer
from apps.accounts.services.otp_service import verify_otp

REFRESH_COOKIE_NAME = "void_refresh"
REFRESH_COOKIE_PATH = "/api/v1/accounts/"
User = get_user_model()

class EmailVerifiedTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_email_verified:
            raise serializers.ValidationError({
                "detail": "Please verify your email before logging in."
            })

        return data

def set_refresh_cookie(response, token):
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )

class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class CookieTokenLoginView(APIView):
    throttle_scope = "auth_login"
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_protect)
    def post(self, request):
        serializer = EmailVerifiedTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens = serializer.validated_data
        user_data = UserProfileSerializer(serializer.user).data
        response = Response({
            "access": tokens["access"],
            "user": user_data,
        })
        set_refresh_cookie(response, tokens["refresh"])
        # print("refresh :",tokens["refresh"], "access",response.data)
        return response

class CookieTokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_protect)
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_token:
            response = Response(
                {"detail": "Refresh cookie is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response)
            return response

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})

        if not serializer.is_valid():
            response = Response(
                serializer.errors,
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_refresh_cookie(response)
            return response

        tokens = serializer.validated_data
        response = Response({"access": tokens["access"]})

        if "refresh" in tokens:
            set_refresh_cookie(response, tokens["refresh"])

        return response


class CookieTokenLogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @method_decorator(csrf_protect)
    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response

class VerifyEmailView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth_verify"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        user = User.objects.filter(email=email).first()

        if not user:
            return Response(
                {"detail": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        success, message = verify_otp(user, otp)

        if not success:
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": message},
            status=status.HTTP_200_OK
        )