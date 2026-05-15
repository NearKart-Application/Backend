from celery import shared_task

# Implemented in Sprint 4
@shared_task
def delete_expired_videos():
    pass

@shared_task
def transcode_video(video_id):
    pass

