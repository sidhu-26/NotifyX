"""
Order serializers — create and read.
"""

from rest_framework import serializers
from .models import Order


class CreateOrderSerializer(serializers.ModelSerializer):
    """Used for creating orders. Only amount is required from the client."""

    class Meta:
        model = Order
        fields = ["amount", "razorpay_order_id"]
        extra_kwargs = {
            "razorpay_order_id": {"required": False},
        }


class OrderSerializer(serializers.ModelSerializer):
    """Full order representation for list/detail views."""

    class Meta:
        model = Order
        fields = ["id", "user", "amount", "status", "razorpay_order_id", "created_at"]
        read_only_fields = fields
