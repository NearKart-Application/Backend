"""
NearKart — Video Views
POST /api/v1/videos/request-upload/
POST /api/v1/videos/<id>/confirm-upload/
GET  /api/v1/videos/my-videos/
GET  /api/v1/videos/feed/
GET  /api/v1/videos/<id>/
PATCH /api/v1/videos/<id>/
DELETE /api/v1/videos/<id>/delete/
POST /api/v1/videos/<id>/like/
GET  /api/v1/videos/<id>/download/
GET  /api/v1/videos/<id>/tags/
POST /api/v1/videos/<id>/tags/
DELETE /api/v1/videos/<id>/tags/<tag_id>/
"""
import logging

from django.conf import settings
from drf_spectacular.utils import (
    OpenApiExample, OpenApiParameter, OpenApiResponse,
    extend_schema, inline_serializer,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import rest_framework.serializers as s

from core.logging import log_event
from core.pagination import StandardOffsetPagination
from core.permissions import IsVendor
from core.utils.cache import CacheService
from core.utils.upload_tracker import UploadTracker
from apps.billing.services import BillingService
from .models import Video, VideoProductTag
from .serializers import (
    VideoSerializer, VideoUploadRequestSerializer,
    VideoProductTagSerializer, VideoProductTagWriteSerializer,
)
from .services import AWSService, VideoService

logger = logging.getLogger(__name__)
_TAG = 'Videos'


class VideoUploadRequestView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Step 1 — Request presigned upload URL (vendor only)',
        description=(
            'Step 1 of 2 for video upload.\n\n'
            'Returns a presigned S3 PUT URL and a `video_id`. '
            'The client uploads the video file directly to S3 using `PUT <upload_url>` '
            'with `Content-Type: video/mp4`. Then call **confirm-upload** to trigger transcoding.\n\n'
            '**Dev mode:** Returns a mock URL — no real S3 upload needed. '
            'Just call confirm-upload with the `video_id` and the video becomes ready instantly.'
        ),
        request=VideoUploadRequestSerializer,
        responses={
            201: OpenApiResponse(
                description='Presigned URL generated',
                response=inline_serializer('UploadRequestResponse', fields={
                    'video_id':          s.UUIDField(),
                    'upload_url':        s.URLField(),
                    'expires_in_seconds': s.IntegerField(),
                    'message':           s.CharField(),
                }),
            ),
            400: OpenApiResponse(description='No store or validation error'),
        },
        examples=[
            OpenApiExample('Request upload URL', request_only=True, value={
                'title': 'New Summer Collection 2026',
                'description': 'Fresh kurtas and dresses for the season.',
            }),
        ],
    )
    def post(self, request):
        if not hasattr(request.user, 'store'):
            return Response(
                {'error': 'validation_error', 'message': 'Create a store first before uploading videos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed, msg = BillingService.check_video_limit(request.user.store)
        if not allowed:
            return Response(
                {'error': 'subscription_required', 'message': msg},
                status=status.HTTP_403_FORBIDDEN,
            )
        upload_allowed, upload_count = UploadTracker.check_and_increment(
            str(request.user.id),
            UploadTracker.MEDIA_VIDEO,
            getattr(settings, 'VIDEO_DAILY_UPLOAD_LIMIT', 10),
        )
        if not upload_allowed:
            return Response(
                {
                    'error': 'daily_limit_reached',
                    'message': (
                        f'Daily video upload limit reached ({upload_count} uploads today). '
                        'Limit resets at midnight.'
                    ),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = VideoUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = None
        product_id = serializer.validated_data.get('product_id')
        if product_id:
            from apps.products.models import Product
            try:
                product = Product.objects.get(id=product_id, store=request.user.store)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'not_found', 'message': 'Product not found in your store.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        video, upload_url = VideoService.request_upload(
            store=request.user.store,
            title=serializer.validated_data['title'],
            description=serializer.validated_data.get('description', ''),
            video_type=serializer.validated_data.get('video_type', 'store_promo'),
            product=product,
        )
        log_event('videos', action='video_upload_requested', video_id=str(video.id),
                  store_id=str(request.user.store.id), user_id=str(request.user.id),
                  title=video.title)
        return Response({
            'video_id': video.id,
            'upload_url': upload_url,
            'expires_in_seconds': getattr(settings, 'AWS_PRESIGNED_URL_EXPIRY', 900),
            'message': (
                'Upload URL ready. PUT your video file to upload_url, '
                'then call /videos/<video_id>/confirm-upload/.'
            ),
        }, status=status.HTTP_201_CREATED)


class VideoConfirmUploadView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Step 2 — Confirm upload done, trigger transcoding (vendor only)',
        description=(
            'Step 2 of 2 for video upload.\n\n'
            'Call this after the S3 PUT upload finishes. Triggers the Celery FFmpeg → HLS task.\n\n'
            '**Dev mode:** Transcoding is skipped. Video is immediately `ready` with mock URLs.'
        ),
        request=inline_serializer('ConfirmUploadRequest', fields={
            'duration_seconds': s.IntegerField(
                required=False, help_text='Video length in seconds (0–60)'
            ),
        }),
        responses={
            200: OpenApiResponse(
                description='Transcoding queued (or completed in dev)',
                response=inline_serializer('ConfirmUploadResponse', fields={
                    'video_id': s.UUIDField(),
                    'status':   s.CharField(),
                    'message':  s.CharField(),
                }),
            ),
            400: OpenApiResponse(description='Already confirmed or wrong state'),
            404: OpenApiResponse(description='Video not found'),
        },
        examples=[
            OpenApiExample('Confirm upload', request_only=True, value={'duration_seconds': 45}),
        ],
    )
    def post(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, store=request.user.store)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if video.status != Video.STATUS_PENDING:
            return Response(
                {'error': 'invalid_state', 'message': f'Video is already in "{video.status}" state.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        max_duration = getattr(settings, 'VIDEO_MAX_DURATION_SECONDS', 60)
        try:
            duration = int(request.data.get('duration_seconds', 0))
        except (TypeError, ValueError):
            duration = 0
        if duration > max_duration:
            return Response(
                {'error': 'validation_error',
                 'message': f'duration_seconds cannot exceed {max_duration} seconds.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        video = VideoService.confirm_upload(video, duration_seconds=duration)
        CacheService.invalidate_video_feeds()
        log_event('videos', action='video_upload_confirmed', video_id=str(video_id),
                  store_id=str(request.user.store.id), user_id=str(request.user.id),
                  status=video.status, duration_seconds=duration)
        return Response({
            'video_id': video.id,
            'status':   video.status,
            'message':  'Transcoding queued. Check GET /videos/<id>/ for status updates.',
        })


class MyVideosView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='List all my videos — all statuses (vendor only)',
        description=(
            'Returns all videos for the vendor\'s store, including `pending_upload`, '
            '`processing`, `failed`, `ready`, and `expired`.\n\n'
            'Use this to check transcoding status after confirm-upload, '
            'or to manage your full video library.'
        ),
        parameters=[
            OpenApiParameter('status', str,
                description='Filter by status: pending_upload | processing | ready | failed | expired',
                required=False),
        ],
        responses={200: VideoSerializer(many=True)},
    )
    def get(self, request):
        if not hasattr(request.user, 'store'):
            return Response({'count': 0, 'next': None, 'previous': None, 'results': []}, status=status.HTTP_200_OK)
        qs = (
            Video.objects
            .filter(store=request.user.store)
            .prefetch_related('product_tags__product')
            .order_by('-created_at')
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        paginator = StandardOffsetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            VideoSerializer(page, many=True, context={'request': request}).data
        )


class VideoUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Update video title / description / visibility (vendor only)',
        description='Partial update — send only the fields you want to change.',
        request=inline_serializer('VideoUpdateRequest', fields={
            'title':       s.CharField(required=False, max_length=200),
            'description': s.CharField(required=False, allow_blank=True),
            'is_visible':  s.BooleanField(required=False),
        }),
        responses={200: VideoSerializer},
        examples=[
            OpenApiExample('Update title and visibility', request_only=True, value={
                'title': 'Revised Summer Collection',
                'is_visible': False,
            }),
        ],
    )
    def patch(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, store=request.user.store)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        update_fields = []
        for field in ('title', 'description', 'video_type'):
            if field in request.data:
                setattr(video, field, request.data[field])
                update_fields.append(field)
        for bool_field in ('is_visible', 'is_pinned'):
            if bool_field in request.data:
                val = request.data[bool_field]
                setattr(video, bool_field, str(val).lower() not in ('false', '0', 'no', ''))
                update_fields.append(bool_field)
        if update_fields:
            update_fields.append('updated_at')
            video.save(update_fields=update_fields)
        return Response(VideoSerializer(video, context={'request': request}).data)


class VideoFeedView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Get location-based video feed (public)',
        description=(
            'Returns ready, visible, non-expired videos near the given coordinates.\n\n'
            'Sorted by distance first, then newest. Max 50 results per call.\n\n'
            '**Dev mode:** After confirm-upload videos are immediately ready. '
            'Use Chennai coords `lat=13.0827, lng=80.2707` to test.'
        ),
        parameters=[
            OpenApiParameter('lat',      float, description='Latitude',                    required=True),
            OpenApiParameter('lng',      float, description='Longitude',                   required=True),
            OpenApiParameter('radius',   int,   description='Radius in km (default 5)',     required=False),
            OpenApiParameter('store_id', str,   description='Filter by store UUID',         required=False),
        ],
        responses={200: VideoSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        try:
            lat    = float(request.query_params['lat'])
            lng    = float(request.query_params['lng'])
            radius = int(request.query_params.get('radius', 5))
        except (KeyError, ValueError):
            return Response(
                {'error': 'validation_error', 'message': 'lat and lng are required numbers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        store_id = request.query_params.get('store_id')
        cache_key = None if store_id else CacheService.video_feed_near_you_key(lat, lng, radius)
        if cache_key:
            cached = CacheService.get(cache_key)
            if cached is not None:
                return Response(cached)
        videos = list(VideoService.get_feed(lat, lng, radius_km=radius, store_id=store_id))
        data   = VideoSerializer(videos, many=True, context={'request': request}).data
        result = {'count': len(data), 'next': None, 'previous': None, 'results': data}
        if cache_key:
            CacheService.set(cache_key, result, timeout=CacheService.TTL_VIDEO_FEED)
        return Response(result)


class VideoDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Get video detail + increment view count (public)',
        description=(
            'Returns full video detail. Increments view_count by 1 on each call.\n\n'
            'Public users only see `ready` + `is_visible=true` videos.\n\n'
            'The store owner (vendor) can see their own video at any status '
            '(pending_upload, processing, failed, etc.) to check transcoding progress.'
        ),
        responses={200: VideoSerializer},
        auth=[],
    )
    def get(self, request, video_id):
        try:
            video = Video.objects.select_related('store').prefetch_related(
                'product_tags__product'
            ).get(id=video_id)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        is_owner = (
            request.user.is_authenticated
            and hasattr(request.user, 'store')
            and video.store_id == request.user.store.id
        )
        if not is_owner and (video.status != Video.STATUS_READY or not video.is_visible):
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if video.status == Video.STATUS_READY:
            VideoService.increment_view(video)
        return Response(VideoSerializer(video, context={'request': request}).data)


class VideoDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Delete video (store owner only)',
        description='Permanently deletes the video. Only the vendor who owns the store can delete.',
        responses={204: None, 404: OpenApiResponse(description='Not found')},
    )
    def delete(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, store=request.user.store)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        store_id = str(video.store_id)
        # Best-effort S3 cleanup before deleting the DB record
        # TODO: replace with a dedicated Celery task (delete_s3_video) when implemented
        raw_key = video.raw_s3_key
        hls_key = video.hls_s3_key
        if raw_key or hls_key:
            try:
                from .services import AWSService
                client = AWSService._client()
                objects_to_delete = [{'Key': k} for k in [raw_key, hls_key] if k]
                if objects_to_delete:
                    from django.conf import settings as _settings
                    client.delete_objects(
                        Bucket=_settings.AWS_S3_BUCKET,
                        Delete={'Objects': objects_to_delete, 'Quiet': True},
                    )
            except Exception as s3_exc:
                logger.warning('VideoDeleteView: S3 cleanup failed for video %s — %s', video_id, s3_exc)
        video.delete()
        CacheService.invalidate_video_feeds()
        log_event('videos', action='video_deleted', video_id=str(video_id),
                  store_id=store_id, user_id=str(request.user.id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class VideoLikeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Like / unlike video (toggle)',
        request=None,
        responses={200: OpenApiResponse(
            response=inline_serializer('VideoLikeResponse', fields={
                'liked':   s.BooleanField(),
                'message': s.CharField(),
            })
        )},
    )
    def post(self, request, video_id):
        try:
            video = Video.objects.select_related('store__owner').get(
                id=video_id, status=Video.STATUS_READY, is_visible=True,
            )
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        liked = VideoService.toggle_like(request.user, video)
        if liked:
            from apps.notifications.services import NotificationService
            NotificationService.notify_video_liked(
                video.store.owner,
                request.user.full_name or request.user.phone_number,
                video.title,
                str(video.id),
            )
        log_event('videos', action='video_liked' if liked else 'video_unliked',
                  video_id=str(video_id), store_id=str(video.store_id),
                  user_id=str(request.user.id))
        return Response({'liked': liked, 'message': 'Liked.' if liked else 'Unliked.'})


class VideoDownloadView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Get presigned download URL for your video (vendor only)',
        description=(
            'Returns a 1-hour presigned S3 GET URL so the vendor can download '
            'the original MP4 locally before it expires.\n\n'
            'Only the store owner can download their own video.\n\n'
            '**Dev mode:** Returns a mock download URL — no real S3 call.\n\n'
            '**Flow:** Vendor receives `video_expiring_soon` push notification '
            '→ taps Download → app calls this endpoint → downloads via the URL.'
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer('VideoDownloadResponse', fields={
                    'video_id':    s.UUIDField(),
                    'title':       s.CharField(),
                    'download_url': s.URLField(),
                    'expires_in':  s.IntegerField(help_text='Seconds until the URL expires'),
                })
            ),
            403: OpenApiResponse(description='Not your video'),
            404: OpenApiResponse(description='Video not found'),
            409: OpenApiResponse(description='Video has no raw file available (already deleted or not yet uploaded)'),
        },
    )
    def get(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, store=request.user.store)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not video.raw_s3_key:
            return Response(
                {'error': 'conflict', 'message': 'No raw file available for this video.'},
                status=status.HTTP_409_CONFLICT,
            )

        expiry_seconds = 3600  # 1 hour
        download_url = AWSService.generate_presigned_download_url(
            video.raw_s3_key, expiry_seconds=expiry_seconds
        )

        return Response({
            'video_id':    str(video.id),
            'title':       video.title,
            'download_url': download_url,
            'expires_in':  expiry_seconds,
        })


class VideoFollowingFeedView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Videos from stores the customer follows',
        description='Returns ready, visible, non-expired videos from all stores the logged-in user follows, newest first.',
        responses={200: VideoSerializer(many=True)},
    )
    def get(self, request):
        videos = list(VideoService.get_following_feed(request.user))
        data   = VideoSerializer(videos, many=True, context={'request': request}).data
        return Response({'count': len(data), 'next': None, 'previous': None, 'results': data})


class VideoTrendingFeedView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Globally trending videos (no radius limit)',
        description='Returns the top 50 ready, visible videos sorted by view_count then like_count. No location filter.',
        responses={200: VideoSerializer(many=True)},
        auth=[],
    )
    def get(self, request):
        key    = CacheService.video_feed_trending_key()
        cached = CacheService.get(key)
        if cached is not None:
            return Response(cached)
        videos = list(VideoService.get_trending_feed())
        data   = VideoSerializer(videos, many=True, context={'request': request}).data
        result = {'count': len(data), 'next': None, 'previous': None, 'results': data}
        CacheService.set(key, result, timeout=CacheService.TTL_VIDEO_TRENDING)
        return Response(result)


class VideoSaveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Save / unsave video (toggle)',
        request=None,
        responses={200: OpenApiResponse(
            response=inline_serializer('VideoSaveResponse', fields={
                'saved':   s.BooleanField(),
                'message': s.CharField(),
            })
        )},
    )
    def post(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, status=Video.STATUS_READY, is_visible=True)
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        saved = VideoService.toggle_save(request.user, video)
        return Response({'saved': saved, 'message': 'Saved.' if saved else 'Unsaved.'})


class VideoTagsView(APIView):
    """
    GET  /videos/<id>/tags/   — list product tags on a video (public)
    POST /videos/<id>/tags/   — add product tag to vendor's own video
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsVendor()]

    @extend_schema(
        tags=[_TAG],
        summary='List product tags on a video (public)',
        responses={200: VideoProductTagSerializer(many=True)},
        auth=[],
    )
    def get(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, status='ready', is_visible=True)
        except Video.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'Video not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        tags = VideoProductTag.objects.filter(video=video).select_related('product')
        return Response(VideoProductTagSerializer(tags, many=True).data)

    @extend_schema(
        tags=[_TAG],
        summary='Pin a product tag on vendor\'s own video',
        description=(
            'Attach a product to a normalised (x_pct, y_pct) position in the video frame. '
            '`product` must be a UUID of a product from the vendor\'s own store. '
            'Max 5 tags per video.'
        ),
        request=VideoProductTagWriteSerializer,
        responses={201: VideoProductTagSerializer, 400: OpenApiResponse(description='Validation error')},
    )
    def post(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id, store=request.user.store)
        except (Video.DoesNotExist, AttributeError):
            return Response({'error': 'not_found', 'message': 'Video not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if VideoProductTag.objects.filter(video=video).count() >= 5:
            return Response(
                {'error': 'validation_error', 'message': 'Maximum 5 product tags per video.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VideoProductTagWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        if product.store_id != request.user.store.id:
            return Response(
                {'error': 'validation_error', 'message': 'Product must belong to your store.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tag, created = VideoProductTag.objects.get_or_create(
            video=video,
            product=product,
            defaults={
                'x_pct': serializer.validated_data['x_pct'],
                'y_pct': serializer.validated_data['y_pct'],
            },
        )
        if not created:
            tag.x_pct = serializer.validated_data['x_pct']
            tag.y_pct = serializer.validated_data['y_pct']
            tag.save(update_fields=['x_pct', 'y_pct'])

        CacheService.invalidate_video_feeds()
        return Response(
            VideoProductTagSerializer(tag).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class VideoTagDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=[_TAG],
        summary='Remove a product tag from vendor\'s own video',
        responses={204: None, 404: OpenApiResponse(description='Not found')},
    )
    def delete(self, request, video_id, tag_id):
        try:
            tag = VideoProductTag.objects.get(
                id=tag_id, video_id=video_id, video__store=request.user.store,
            )
        except (VideoProductTag.DoesNotExist, AttributeError):
            return Response({'error': 'not_found', 'message': 'Tag not found.'},
                            status=status.HTTP_404_NOT_FOUND)
        tag.delete()
        CacheService.invalidate_video_feeds()
        return Response(status=status.HTTP_204_NO_CONTENT)
