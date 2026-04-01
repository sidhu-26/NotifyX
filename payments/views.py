"""
Payment webhook view — handles Razorpay webhook callbacks.
This is the source of truth for payment status updates.
"""

import json
import logging

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as drf_serializers

from orders.models import Order

logger = logging.getLogger("payments")


@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    """
    POST /api/payments/webhook/
    
    Handles Razorpay webhook events:
      - payment.captured → mark order as PAID
      - payment.failed   → mark order as FAILED

    No auth required (webhooks come from Razorpay).
    Signature verification is a placeholder for now.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No auth for webhooks

    @extend_schema(
        tags=["Payments"],
        description="Razorpay webhook endpoint. Handles payment.captured and payment.failed events.",
        request=inline_serializer(
            name="RazorpayWebhookPayload",
            fields={
                "event": drf_serializers.CharField(help_text="e.g. payment.captured"),
                "payload": drf_serializers.DictField(help_text="Razorpay payload with payment entity"),
            },
        ),
        responses=inline_serializer(
            name="WebhookResponse",
            fields={"detail": drf_serializers.CharField()},
        ),
    )
    def post(self, request):
        payload = request.data

        # Log the incoming webhook payload
        logger.info(f"Webhook received: {json.dumps(payload, indent=2, default=str)}")

        # --- Signature verification placeholder ---
        # In production, verify the webhook signature using:
        # razorpay_signature = request.headers.get("X-Razorpay-Signature")
        # razorpay_client.utility.verify_webhook_signature(body, signature, secret)
        # For now, we trust the payload.

        # Extract event type
        event = payload.get("event")
        if not event:
            logger.warning("Webhook received without event type")
            return Response(
                {"detail": "Missing event type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract order ID from payload
        # Razorpay nests payment info under payload.payment.entity
        try:
            payment_entity = payload["payload"]["payment"]["entity"]
            razorpay_order_id = payment_entity.get("order_id")
            razorpay_payment_id = payment_entity.get("id")
        except (KeyError, TypeError):
            logger.error("Webhook payload missing expected structure")
            return Response(
                {"detail": "Invalid payload structure"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not razorpay_order_id:
            logger.warning(f"No order_id in webhook payload (payment: {razorpay_payment_id})")
            return Response(
                {"detail": "Missing order_id in payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the order
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found for razorpay_order_id: {razorpay_order_id}")
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Handle events
        if event == "payment.captured":
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])
            logger.info(f"Order #{order.id} marked as PAID (payment: {razorpay_payment_id})")

        elif event == "payment.failed":
            order.status = Order.Status.FAILED
            order.save(update_fields=["status"])
            logger.info(f"Order #{order.id} marked as FAILED (payment: {razorpay_payment_id})")

        else:
            logger.info(f"Unhandled webhook event: {event}")
            return Response({"detail": f"Event '{event}' not handled"})

        return Response({"detail": "Webhook processed successfully"})
