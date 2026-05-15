from celery import shared_task

# Implemented in Sprint 5
@shared_task
def send_push_notification(user_id, title, body, data=None):
    pass

