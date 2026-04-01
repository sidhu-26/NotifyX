"""
Account URL configuration.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # Profile
    path("me/", views.CurrentUserView.as_view(), name="current-user"),

    # Email verification
    path("verify-email/send/", views.SendVerificationView.as_view(), name="verify-email-send"),
    path("verify-email/verify/", views.VerifyEmailView.as_view(), name="verify-email-verify"),
]
