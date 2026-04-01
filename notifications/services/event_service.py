def create_event(event_type, user_id, payload):
    """
    Simulates event creation. This will later push events to Redis/Celery queue.
    """
    print(f"\n[EVENT DISPATCHED] Type: {event_type} | User: {user_id} | Payload: {payload}\n")
