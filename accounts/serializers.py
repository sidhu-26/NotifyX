"""
Account serializers — registration, login, user profile, email verification.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password", "username"]
        extra_kwargs = {
            "username": {"required": False},
        }

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    """Read-only user representation."""

    class Meta:
        model = User
        fields = ["id", "email", "username", "is_email_verified", "is_active", "created_at"]
        read_only_fields = fields


class SendVerificationSerializer(serializers.Serializer):
    """No input needed — sends verification to the authenticated user's email."""
    pass


class VerifyEmailSerializer(serializers.Serializer):
    """Accepts the verification token."""
    token = serializers.CharField()
