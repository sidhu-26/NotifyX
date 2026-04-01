"""
Order views — create order and list user's orders.
"""

import logging

import razorpay
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer

logger = logging.getLogger("orders")


@extend_schema(tags=["Orders"])
class CreateOrderView(CreateAPIView):
    """
    POST /api/orders/
    Create a new order for the authenticated user.
    """
    serializer_class = CreateOrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        amount = serializer.validated_data["amount"]

        # 1. Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # 2. Create order in Razorpay
        try:
            razorpay_order = client.order.create({
                "amount": amount,
                "currency": "INR",
                "payment_capture": "1"  # auto capture
            })
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            raise APIException("Failed to create order with payment gateway")

        # 3. Save to our database with the razorpay_order_id
        order = serializer.save(
            user=self.request.user,
            razorpay_order_id=razorpay_order["id"]
        )
        logger.info(f"Order #{order.id} created by {self.request.user.email} — ₹{order.amount / 100:.2f}")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full order representation
        output = OrderSerializer(serializer.instance)
        return Response(output.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Orders"])
class ListOrdersView(ListAPIView):
    """
    GET /api/orders/
    List all orders for the authenticated user.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
