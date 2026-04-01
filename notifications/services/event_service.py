"""
Event dispatcher mapping webhook/domain events to async Celery tasks.
"""

from notifications.tasks import process_notification_event

def create_event(event_type, user_id, payload):
    """
    Fire-and-forget event dispatcher.
    Offloads heavy lifting to Celery queue via Redis broker.
    """
    # Push to Celery
    process_notification_event.delay(event_type, user_id, payload)
    
    # We can still print to console to show the API call finished instantly
    print(f"\n[EVENT ENQUEUED TO CELERY] Type: {event_type} | User: {user_id}\n")
