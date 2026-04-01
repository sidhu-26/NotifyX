import logging
import json
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Notification

logger = logging.getLogger("notifications.tasks")
User = get_user_model()

@shared_task(name="notifications.process_event")
def process_notification_event(event_type, user_id, payload):
    """
    Asynchronously processes a domain event (like payment success/failure).
    Creates a Notification model and actually sends an email channel.
    """
    logger.info(f"[CELERY TASK START] Event: {event_type} | UserID: {user_id}")
    
    # 1. Create robust Notification Record
    notification = Notification.objects.create(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
        status="PENDING"
    )
    
    # 2. Fetch User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found. Hard failing.")
        notification.status = "FAILED"
        notification.save(update_fields=["status"])
        return False

    # 3. Simulate Email Channel (Uses Console Backend for local tests)
    try:
        subject = f"NotifyX Update: {event_type}"
        message = (
            f"Hello {user.email},\n\n"
            f"We received a new event regarding your account.\n"
            f"Event Type: {event_type}\n"
            f"Payload: {json.dumps(payload, indent=2)}\n\n"
            f"Thanks,\nNotifyX Support"
        )
        
        # Django's built in send_mail blocks, but this is fine since we are in Celery!
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        # Success!
        notification.status = "SENT"
        notification.save(update_fields=["status"])
        logger.info(f"[CELERY TASK DONE] Successfully sent email and updated status to SENT for {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {user.email}: {e}")
        notification.status = "FAILED"
        notification.save(update_fields=["status"])
        return False
