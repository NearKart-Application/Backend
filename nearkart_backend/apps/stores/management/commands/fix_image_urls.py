"""
Management command: fix_image_urls

Strips expired query-string parameters from S3 presigned URLs stored in the DB.
Presigned URLs look like:
  https://bucket.s3.region.amazonaws.com/media/stores/x/logo.jpg?X-Amz-Algorithm=...
After stripping the query string they become permanent public URLs:
  https://bucket.s3.region.amazonaws.com/media/stores/x/logo.jpg

Run once after deploying the querystring_auth=False fix:
  python manage.py fix_image_urls
  python manage.py fix_image_urls --dry-run   (preview only, no DB writes)
"""
from urllib.parse import urlparse, urlunparse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.stores.models import Store
from apps.products.models import ProductImage
from apps.admin_panel.models import PromoBanner


def strip_qs(url: str) -> str:
    """Remove query string from a URL; return unchanged if not an S3 presigned URL."""
    if not url:
        return url
    if 'X-Amz-' not in url:
        return url
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query='', fragment=''))


class Command(BaseCommand):
    help = 'Strip expired S3 presigned URL query strings from all image URL fields'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print what would be changed without writing to the database'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        total_fixed = 0

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved\n'))

        with transaction.atomic():
            # ── Store logo_url + banner_url ───────────────────────────────────
            stores = Store.objects.exclude(logo_url='').exclude(logo_url__isnull=True) | \
                     Store.objects.exclude(banner_url='').exclude(banner_url__isnull=True)
            stores = Store.objects.all()

            for store in stores:
                changed = False
                new_logo   = strip_qs(store.logo_url   or '')
                new_banner = strip_qs(store.banner_url or '')
                new_qr     = strip_qs(getattr(store, 'qr_code_url', '') or '')

                if new_logo != (store.logo_url or ''):
                    self.stdout.write(f'  Store {store.id}  logo_url: {store.logo_url[:60]}... → stripped')
                    store.logo_url = new_logo
                    changed = True
                if new_banner != (store.banner_url or ''):
                    self.stdout.write(f'  Store {store.id}  banner_url: stripped')
                    store.banner_url = new_banner
                    changed = True
                if hasattr(store, 'qr_code_url') and new_qr != (store.qr_code_url or ''):
                    store.qr_code_url = new_qr
                    changed = True

                if changed:
                    total_fixed += 1
                    if not dry_run:
                        update_fields = [f for f in ['logo_url', 'banner_url', 'qr_code_url']
                                         if hasattr(store, f)]
                        store.save(update_fields=update_fields)

            self.stdout.write(f'Stores fixed: {total_fixed}')
            count = total_fixed

            # ── ProductImage.image_url ────────────────────────────────────────
            pi_fixed = 0
            for pi in ProductImage.objects.exclude(image_url='').exclude(image_url__isnull=True):  # type: ignore[attr-defined]
                new_url = strip_qs(pi.image_url)
                if new_url != pi.image_url:
                    pi.image_url = new_url
                    pi_fixed += 1
                    if not dry_run:
                        pi.save(update_fields=['image_url'])

            self.stdout.write(f'ProductImages fixed: {pi_fixed}')
            total_fixed += pi_fixed

            # ── User avatar ───────────────────────────────────────────────────
            User = get_user_model()
            avatar_field = 'avatar'
            if hasattr(User, avatar_field):
                av_fixed = 0
                for user in User.objects.exclude(**{f'{avatar_field}__isnull': True}).exclude(**{avatar_field: ''}):
                    old = getattr(user, avatar_field)
                    new = strip_qs(old)
                    if new != old:
                        setattr(user, avatar_field, new)
                        av_fixed += 1
                        if not dry_run:
                            user.save(update_fields=[avatar_field])
                self.stdout.write(f'User avatars fixed: {av_fixed}')
                total_fixed += av_fixed

            # ── PromoBanner image_url ─────────────────────────────────────────
            try:
                pb_fixed = 0
                for pb in PromoBanner.objects.exclude(image_url='').exclude(image_url__isnull=True):
                    new_url = strip_qs(pb.image_url)
                    if new_url != pb.image_url:
                        pb.image_url = new_url
                        pb_fixed += 1
                        if not dry_run:
                            pb.save(update_fields=['image_url'])
                self.stdout.write(f'PromoBanners fixed: {pb_fixed}')
                total_fixed += pb_fixed
            except Exception:
                pass

            if dry_run:
                transaction.set_rollback(True)

        verb = 'Would fix' if dry_run else 'Fixed'
        self.stdout.write(self.style.SUCCESS(f'\n{verb} {total_fixed} image URL(s) total.'))
        if dry_run:
            self.stdout.write('Run without --dry-run to apply.')
        else:
            self.stdout.write('Done. New uploads will use permanent public URLs automatically.')
