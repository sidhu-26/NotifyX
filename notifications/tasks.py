import logging
import json
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from core.redis_client import increment_key

from .models import Notification

logger = logging.getLogger("notifications.tasks")
User = get_user_model()


class EmailChannel:
    """ Extensible channel interface for dispatching emails. """
    def send(self, user, event_type, payload):
        subject = f"NotifyX Update: {event_type}"
        message = (
            f"Hello {user.email},\n\n"
            f"We received a new event regarding your account.\n"
            f"Event Type: {event_type}\n"
            f"Payload: {json.dumps(payload, indent=2)}\n\n"
            f"Thanks,\nNotifyX Support"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


def is_rate_limited(user_id):
    """ Uses increment+expire to enforce a ceiling of 5 notifications per 60 seconds per user """
    key = f"rate:notifications:{user_id}"
    count = increment_key(key, 60)
    return count > 5

@shared_task(name="notifications.process_event", bind=True, max_retries=5)
def process_notification_event(self, event_type, user_id, payload):
    """
    Asynchronously processes a domain event (like payment success/failure),
    with idempotency, state tracking, and exponential backoff retries.
    """
    # 1. Generate Idempotency Key
    order_id = payload.get("order_id", "unknown_order")
    idempotency_key = f"{event_type}_{user_id}_{order_id}"
    
    logger.info(f"[CELERY TASK START] Key: {idempotency_key} | Retry: {self.request.retries}")

    # 2. Prevent Duplicates (Idempotency)
    notification, created = Notification.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "user_id": user_id,
            "event_type": event_type,
            "payload": payload,
            "status": Notification.Status.PENDING,
            "retry_count": 0,
        }
    )

    if not created and notification.status in [Notification.Status.SENT, Notification.Status.PROCESSING]:
        logger.info(f"[IDEMPOTENCY] Notification {idempotency_key} already {notification.status}. Skipping duplicate.")
        return True

    # 3. Mark as PROCESSING
    notification.status = Notification.Status.PROCESSING
    notification.retry_count = self.request.retries
    notification.save(update_fields=["status", "retry_count"])

    try:
        # Simulate Failure if requested
        if payload.get("simulate_failure"):
            raise Exception("Simulated Failure for Testing")

        # 4. Fetch User
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found. Hard failing.")
            notification.status = list(Notification.Status.FAILED)[0] if isinstance(Notification.Status.FAILED, tuple) else Notification.Status.FAILED
            notification.save(update_fields=["status"])
            return False

        # 5. Enforce Rate Limiting before dispatch
        if is_rate_limited(user_id):
            logger.warning(f"[RATE LIMIT] User {user_id} hit rate ceiling. Throttling {idempotency_key}.")
            notification.status = Notification.Status.FAILED
            notification.save(update_fields=["status"])
            return False

        # 6. Send via specific Channel implementation
        email_channel = EmailChannel()
        email_channel.send(user, event_type, payload)
        
        # 7. Success
        notification.status = Notification.Status.SENT
        notification.save(update_fields=["status"])
        logger.info(f"[CELERY TASK DONE] Successfully sent email and updated status to SENT for {idempotency_key}")
        return True
        
    except Exception as exc:
        # 7. Handle Failure & Auto-Retry
        logger.error(f"[CELERY TASK FAILED] Error for {idempotency_key}: {str(exc)}")
        
        # Track DB retry count explicitly
        notification.retry_count = self.request.retries + 1
        
        # Check against retry limit before raising retry
        if self.request.retries >= self.max_retries:
            logger.error(f"[MAX RETRIES REACHED] Forcing graceful exit for {idempotency_key} and tossing into DLQ.")
            notification.status = Notification.Status.FAILED
            notification.save(update_fields=["status", "retry_count"])
            
            # --- Dead Letter Queue Logic ---
            from .models import DeadLetterQueue
            DeadLetterQueue.objects.create(
                event_type=event_type,
                user_id=user_id,
                payload=payload,
                error_message=str(exc)
            )
            logger.info(f"[DLQ] Successfully captured permanently failed event {idempotency_key} into Dead Letter Queue database table.")
            
            return False
            
        # Set Explicit RETRY state
        notification.status = Notification.Status.RETRY
        notification.save(update_fields=["status", "retry_count"])
        
        # Calculate exponential backoff: 2, 4, 8, 16, 32 seconds
        countdown = 2 ** (self.request.retries + 1)
        logger.info(f"[CELERY RETRY] Scheduled retry {self.request.retries + 1}/{self.max_retries} in {countdown}s...")
        
        raise self.retry(exc=exc, countdown=countdown)
