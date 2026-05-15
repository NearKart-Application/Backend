"""
NearKart — Store Services
StoreService, QRService
"""
import io
import logging
from django.contrib.gis.geos import Point

from core.utils.cache import CacheService
from core.utils.geo import get_nearby_stores, reverse_geocode

logger = logging.getLogger(__name__)


class StoreService:

    @staticmethod
    def create(user, validated_data: dict):
        from .models import Store
        lat = validated_data.pop('latitude')
        lng = validated_data.pop('longitude')
        location = Point(lng, lat, srid=4326)
        locality = reverse_geocode(lat, lng)
        store = Store.objects.create(
            owner=user,
            location=location,
            locality=locality,
            **validated_data,
        )
        return store

    @staticmethod
    def update(store, validated_data: dict):
        lat = validated_data.pop('latitude', None)
        lng = validated_data.pop('longitude', None)
        if lat is not None and lng is not None:
            store.location = Point(lng, lat, srid=4326)
            store.locality = reverse_geocode(lat, lng)
            CacheService.invalidate_store_caches(lat, lng)
        for attr, value in validated_data.items():
            setattr(store, attr, value)
        store.save()
        CacheService.delete(CacheService.store_detail_key(str(store.id)))
        return store

    @staticmethod
    def get_nearby(lat: float, lng: float, radius_km: int = 2, category: str = None):
        return get_nearby_stores(lat, lng, radius_km, category)

    @staticmethod
    def toggle_follow(user, store):
        from .models import StoreFollow
        from apps.notifications.services import NotificationService
        follow, created = StoreFollow.objects.get_or_create(user=user, store=store)
        if not created:
            follow.delete()
            return False  # unfollowed
        NotificationService.notify_new_follower(
            store.owner,
            user.full_name or user.phone_number,
        )
        return True  # followed

    @staticmethod
    def add_review(user, store, rating: int, comment: str = ''):
        from .models import StoreReview
        from apps.notifications.services import NotificationService
        review, created = StoreReview.objects.update_or_create(
            user=user, store=store,
            defaults={'rating': rating, 'comment': comment},
        )
        # Recalculate store performance score
        avg = store.reviews.aggregate(
            avg=__import__('django.db.models', fromlist=['Avg']).Avg('rating')
        )['avg'] or 0
        store.performance_score = round(avg, 2)
        store.save(update_fields=['performance_score'])
        NotificationService.notify_new_review(
            store.owner,
            user.full_name or user.phone_number,
            rating,
            store.name,
        )
        return review


class QRService:

    @staticmethod
    def generate_and_upload(store) -> str:
        """
        Generates a QR code image for the store, uploads to S3,
        saves CDN URL to store.qr_code_url and returns it.
        """
        try:
            import qrcode
            from core.utils.s3 import get_s3_client, get_cdn_url
            from django.conf import settings

            store_url = f'https://nearkart.in/stores/{store.id}'
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(store_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            s3 = get_s3_client()
            s3_key = f'qrcodes/{store.id}/qr.png'
            s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key,
                Body=buffer.getvalue(),
                ContentType='image/png',
            )

            cdn_url = get_cdn_url(s3_key)
            store.qr_code_url = cdn_url
            store.save(update_fields=['qr_code_url'])
            return cdn_url

        except Exception as e:
            logger.error(f'QR code generation failed for store {store.id}: {e}')
            return ''
