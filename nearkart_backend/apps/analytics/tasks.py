from celery import shared_task

# Implemented in Sprint 8
@shared_task
def aggregate_daily_stats():
    pass

@shared_task
def send_weekly_digest_emails():
    pass

