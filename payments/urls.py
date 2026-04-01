"""
Payment URL configuration.
"""

from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("webhook/", views.RazorpayWebhookView.as_view(), name="razorpay-webhook"),
]
