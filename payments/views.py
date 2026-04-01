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
from notifications.services.event_service import create_event

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

        # Extract order ID and payment ID from payload
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

        logger.info(f"Processing webhook: event={event}, order_id={razorpay_order_id}, payment_id={razorpay_payment_id}")

        # --- Idempotency check: reject duplicate payment IDs ---
        if razorpay_payment_id and Order.objects.filter(razorpay_payment_id=razorpay_payment_id).exists():
            logger.info(f"Duplicate webhook ignored — payment {razorpay_payment_id} already processed")
            return Response({"detail": "Already processed"})

        # Find the order
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
        except Order.DoesNotExist:
            logger.error(f"Order not found for razorpay_order_id: {razorpay_order_id}")
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Handle events with idempotency — only update if status actually changes
        if event == "payment.captured":
            if order.status == Order.Status.PAID:
                logger.info(f"Order #{order.id} already PAID — skipping duplicate webhook")
                return Response({"detail": "Already processed"})

            order.status = Order.Status.PAID
            order.razorpay_payment_id = razorpay_payment_id
            order.save(update_fields=["status", "razorpay_payment_id"])
            logger.info(f"Order #{order.id} marked as PAID (payment: {razorpay_payment_id})")

            # --- Emit Async Event ---
            create_event(
                event_type="payment_success",
                user_id=order.user.id,
                payload={
                    "order_id": order.id,
                    "amount": order.amount
                }
            )

        elif event == "payment.failed":
            if order.status == Order.Status.FAILED:
                logger.info(f"Order #{order.id} already FAILED — skipping duplicate webhook")
                return Response({"detail": "Already processed"})

            order.status = Order.Status.FAILED
            order.razorpay_payment_id = razorpay_payment_id
            order.save(update_fields=["status", "razorpay_payment_id"])
            logger.info(f"Order #{order.id} marked as FAILED (payment: {razorpay_payment_id})")

            # --- Emit Async Event ---
            create_event(
                event_type="payment_failed",
                user_id=order.user.id,
                payload={
                    "order_id": order.id,
                    "amount": order.amount
                }
            )

        else:
            logger.info(f"Unhandled webhook event: {event}")
            return Response({"detail": f"Event '{event}' not handled"})

        return Response({"detail": "Webhook processed successfully"})

