"""
Order model — minimal order tracking for the e-commerce foundation.
"""

from django.conf import settings
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    amount = models.PositiveIntegerField(help_text="Amount in paise (e.g. 50000 = ₹500)")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Razorpay order ID for webhook matching",
    )
    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        help_text="Razorpay payment ID — used for idempotency (reject duplicate webhooks)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} — {self.user.email} — {self.status}"
