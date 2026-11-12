from rest_framework import generics 
from rest_framework.permissions import AllowAny,IsAuthenticated
from .serializers import RegisterSerializer,UserProfileSerializer
from apps.accounts.services.email_service import send_verification_email

class RegisterView(generics.CreateAPIView):
    throttle_scope = "auth_register"
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        send_verification_email(user)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

# $env:DB_NAME = "void_db"
# $env:DB_USER = "void_user"
# $env:DB_PASSWORD = "risaldanish10"
# $env:DB_HOST = "127.0.0.1"
# $env:DB_PORT = "5432"

