"""
Event dispatcher mapping webhook/domain events to async Celery tasks.
"""

from notifications.tasks import process_notification_event

def create_event(event_type, user_id, payload):
    """
    Fire-and-forget event dispatcher.
    Offloads heavy lifting to Celery queue via Redis broker.
    Routes intelligently to 'high_priority' or 'low_priority' queue contexts.
    """
    # Route payment events directly to High Priority
    queue_name = "high_priority" if event_type.startswith("payment") else "low_priority"

    # Push to dynamically routed Celery Queue
    process_notification_event.apply_async(
        args=[event_type, user_id, payload],
        queue=queue_name
    )
    
    print(f"\n[EVENT ENQUEUED TO CELERY] Type: {event_type} | User: {user_id} | Queue: {queue_name}\n")


def retry_dlq_event(dlq_id):
    """
    Recovers a dead-lettered event and injects it back into the high_priority queue.
    This turns the DLQ from static storage into a recoverable system!
    """
    from notifications.models import DeadLetterQueue
    
    dlq = DeadLetterQueue.objects.get(id=dlq_id)

    process_notification_event.apply_async(
        args=[dlq.event_type, dlq.user_id, dlq.payload],
        queue="high_priority"
    )
    
    print(f"[DLQ RECOVERY] Successfully re-queued event '{dlq.event_type}' from DLQ ID {dlq_id} for user {dlq.user_id}")
