"""
Account views — register, current user, email verification.
Login/token is handled by SimpleJWT's built-in views.
"""

import logging
import uuid

from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers

from core.redis_client import set_key, get_key, delete_key
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)

logger = logging.getLogger("accounts")

# Redis key prefix for email verification tokens
VERIFY_TOKEN_PREFIX = "email_verify:"
VERIFY_TOKEN_TTL = 3600  # 1 hour


@extend_schema(tags=["Accounts"])
class RegisterView(CreateAPIView):
    """
    POST /api/accounts/register/
    Create a new user account.
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info(f"User registered: {user.email}")


class CurrentUserView(APIView):
    """
    GET /api/accounts/me/
    Returns the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        responses=UserSerializer,
        description="Returns the authenticated user's profile.",
    )

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class SendVerificationView(APIView):
    """
    POST /api/accounts/verify-email/send/
    Generates a verification token, stores it in Redis, and returns it.
    In production, this would send an email — for now we return the token
    in the response for testing.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Accounts"],
        request=None,
        responses=inline_serializer(
            name="VerificationTokenResponse",
            fields={
                "detail": drf_serializers.CharField(),
                "token": drf_serializers.CharField(),
            },
        ),
        description="Generates a verification token. In production, this would be emailed.",
    )

    def post(self, request):
        user = request.user

        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate token and store in Redis
        token = uuid.uuid4().hex
        redis_key = f"{VERIFY_TOKEN_PREFIX}{token}"
        set_key(redis_key, str(user.id), ttl=VERIFY_TOKEN_TTL)

        logger.info(f"Verification token generated for {user.email}")

        # In production, send email here. For now, return token directly.
        return Response({
            "detail": "Verification token generated.",
            "token": token,  # Remove this in production — send via email instead
        })


class VerifyEmailView(APIView):
    """
    POST /api/accounts/verify-email/verify/
    Accepts a token and marks the user's email as verified.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Accounts"],
        request=VerifyEmailSerializer,
        responses=inline_serializer(
            name="VerifyEmailResponse",
            fields={"detail": drf_serializers.CharField()},
        ),
        description="Verify email using the token received.",
    )

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        redis_key = f"{VERIFY_TOKEN_PREFIX}{token}"

        # Look up token in Redis
        user_id = get_key(redis_key)
        if not user_id:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark user as verified
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(id=int(user_id))
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        # Clean up token
        delete_key(redis_key)

        logger.info(f"Email verified for {user.email}")
        return Response({"detail": "Email verified successfully."})
