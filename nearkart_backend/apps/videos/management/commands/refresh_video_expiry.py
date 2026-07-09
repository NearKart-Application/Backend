"""
Management command: refresh_video_expiry

Resets expires_at to 10 years from now for all videos that are status=ready
and is_visible=True but have already expired. Useful for dev environments
where seed videos expire after 30 days.

Run:
    python manage.py refresh_video_expiry
    python manage.py refresh_video_expiry --days 3650   (default: 3650)
    python manage.py refresh_video_expiry --all         (refresh ALL ready videos, even non-expired)
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.videos.models import Video


class Command(BaseCommand):
    help = 'Refresh expires_at for expired-but-ready videos (dev helper)'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3650,
                            help='How many days from now to set expiry (default: 3650)')
        parser.add_argument('--all', action='store_true',
                            help='Refresh ALL ready+visible videos, not just expired ones')

    def handle(self, *args, **options):
        days = options['days']
        refresh_all = options['all']
        new_expiry = timezone.now() + timedelta(days=days)

        # Revive videos that Celery already flipped to status=expired
        revived = Video.objects.filter(
            status=Video.STATUS_EXPIRED, is_visible=False,
            video_url__isnull=False,
        ).update(
            status=Video.STATUS_READY,
            is_visible=True,
            expires_at=new_expiry,
        )

        # Also refresh ready videos that are about to expire (or all, if --all)
        qs = Video.objects.filter(status=Video.STATUS_READY, is_visible=True)
        if not refresh_all:
            qs = qs.filter(expires_at__lte=timezone.now())
        refreshed = qs.update(expires_at=new_expiry)

        total = revived + refreshed
        if total == 0:
            self.stdout.write(self.style.WARNING('No videos needed refreshing.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'✅ Revived {revived} expired video(s), refreshed {refreshed} ready video(s) — '
            f'expires_at set to {new_expiry.strftime("%Y-%m-%d")} ({days} days from now)'
        ))
