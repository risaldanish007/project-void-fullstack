from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only = True,
        validators = [validate_password],
    )

    class Meta:
        model = User
        fields = ("id","email","first_name","last_name","password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)

        user.is_active = False
        user.is_email_verified = False
        user.save(update_fields=["is_active", "is_email_verified"])

        return user

class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "name",
            "is_staff",
            "is_active",
            "role",
            "status",
        )
        read_only_fields = ("id", "email", "is_staff", "is_active", "role", "status", "name")

    def get_role(self, obj):
        return "admin" if (obj.is_staff or obj.is_superuser) else "customer"

    def get_status(self, obj):
        return "Active" if obj.is_active else "Banned"

    def get_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name if full_name else obj.email.split("@")[0]

class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        trim_whitespace=False,
        write_only=True,
    )

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError(
                "OTP must contain exactly 6 digits."
            )

        return value
