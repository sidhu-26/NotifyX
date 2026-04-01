from django.conf import settings
from django.db import models

class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        RETRY = "RETRY", "Retry"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    event_type = models.CharField(max_length=100)
    status = models.CharField(default=Status.PENDING, max_length=20, choices=Status.choices)
    payload = models.JSONField()
    
    idempotency_key = models.CharField(max_length=255, unique=True)
    retry_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification #{self.id} — {self.user.email} — {self.event_type} — {self.status}"
