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

from core.permissions import IsVendor
from apps.billing.services import BillingService
from .models import Video
from .serializers import VideoSerializer, VideoUploadRequestSerializer
from .services import VideoService

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
                {'error': 'plan_limit_reached', 'message': msg},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = VideoUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        video, upload_url = VideoService.request_upload(
            store=request.user.store,
            title=serializer.validated_data['title'],
            description=serializer.validated_data.get('description', ''),
        )
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
            return Response([], status=status.HTTP_200_OK)
        qs = Video.objects.filter(store=request.user.store).order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(VideoSerializer(qs, many=True, context={'request': request}).data)


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
        allowed = {'title', 'description', 'is_visible'}
        update_fields = []
        for field in allowed:
            if field in request.data:
                setattr(video, field, request.data[field])
                update_fields.append(field)
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
        videos = VideoService.get_feed(lat, lng, radius_km=radius, store_id=store_id)
        return Response(VideoSerializer(videos, many=True, context={'request': request}).data)


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
            video = Video.objects.select_related('store').get(id=video_id)
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
        video.delete()
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
            video = Video.objects.get(
                id=video_id, status=Video.STATUS_READY, is_visible=True,
            )
        except Video.DoesNotExist:
            return Response(
                {'error': 'not_found', 'message': 'Video not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        liked = VideoService.toggle_like(request.user, video)
        return Response({'liked': liked, 'message': 'Liked.' if liked else 'Unliked.'})
