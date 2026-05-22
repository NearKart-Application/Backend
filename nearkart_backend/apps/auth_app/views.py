"""
NearKart — Auth Views
POST /api/v1/auth/otp/send/
POST /api/v1/auth/otp/verify/
POST /api/v1/auth/token/refresh/
GET  /api/v1/auth/me/
PATCH /api/v1/auth/me/
PUT  /api/v1/auth/me/location/
POST /api/v1/auth/logout/
"""
import logging
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample, inline_serializer
from drf_spectacular.openapi import AutoSchema
import rest_framework.serializers as s

from .serializers import (
    OTPSendSerializer,
    OTPVerifySerializer,
    UserSerializer,
    UserSearchSerializer,
    LocationUpdateSerializer,
)
from .services import OTPService, JWTService

logger = logging.getLogger(__name__)

_TAG = 'Auth'


class OTPSendView(APIView):
    permission_classes = [AllowAny]
    # throttle_scope replaced by sliding-window rate limiter (see post() below)

    @extend_schema(
        tags=[_TAG],
        summary='Send OTP',
        description=(
            'Send a 6-digit OTP to the given Indian mobile number.\n\n'
            '**Format:** `+91XXXXXXXXXX` — must start with `+91` followed by 10 digits (first digit must be 6–9).\n\n'
            '**Valid examples:** `+919999999999`, `+916543210987`\n\n'
            '**Invalid examples:** `9999999999` (no +91), `+91 9999999999` (no spaces), `919999999999` (missing +)\n\n'
            '**Dev mode:** OTP is always `123456` — no real SMS is sent.'
        ),
        request=OTPSendSerializer,
        examples=[
            OpenApiExample(
                'Vendor phone',
                request_only=True,
                value={'phone_number': '+919999999999'},
            ),
            OpenApiExample(
                'Customer phone',
                request_only=True,
                value={'phone_number': '+916000000001'},
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='OTP sent successfully',
                response=inline_serializer('OTPSendResponse', fields={
                    'message': s.CharField(),
                }),
                examples=[OpenApiExample('Success', value={'message': 'OTP sent successfully'})],
            ),
            400: OpenApiResponse(
                description='Invalid phone number format',
                response=inline_serializer('OTPSendError', fields={
                    'error': s.CharField(),
                    'message': s.CharField(),
                    'code': s.CharField(),
                    'details': s.DictField(),
                }),
                examples=[OpenApiExample('Bad phone', value={
                    'error': 'validation_error',
                    'message': 'Enter a valid Indian mobile number in +91XXXXXXXXXX format.',
                    'code': 'ERROR',
                    'details': {'phone_number': ['Enter a valid Indian mobile number in +91XXXXXXXXXX format.']},
                })],
            ),
        },
        auth=[],
    )
    def post(self, request):
        serializer = OTPSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']

        # Algorithm 6 — Sliding window: 5 OTPs per phone per hour.
        # Dev bypass: permanent QA accounts skip rate limiting so load tests
        # and multi-device QA can authenticate freely (DEBUG mode only).
        from django.conf import settings as _s
        from core.utils.cache import CacheService
        is_dev_bypass = phone_number in getattr(_s, 'DEV_BYPASS_PHONES', set())
        if not is_dev_bypass and CacheService.is_rate_limited(
            f'otp:{phone_number}', max_requests=5, window_secs=3600
        ):
            return Response(
                {'error': 'rate_limited', 'message': 'Too many OTP requests. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        OTPService.generate_and_send(phone_number)
        return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Verify OTP and login',
        description=(
            'Verify the OTP and get JWT access + refresh tokens.\n\n'
            '**Step 1:** Call `/auth/otp/send/` first to generate an OTP.\n\n'
            '**Step 2:** Enter the phone number and OTP here.\n\n'
            '**Dev mode:** OTP is always `123456` — use that in the example below.\n\n'
            'New users are created automatically on first login.\n\n'
            '**After success:** Copy the `access` token and click **Authorize** (top of page) → paste as `Bearer <token>`'
        ),
        request=OTPVerifySerializer,
        examples=[
            OpenApiExample(
                'Vendor login (dev)',
                request_only=True,
                value={'phone_number': '+919999999999', 'otp': '123456'},
            ),
            OpenApiExample(
                'Customer login (dev)',
                request_only=True,
                value={'phone_number': '+916000000001', 'otp': '123456'},
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='Login successful — returns JWT tokens',
                response=inline_serializer('OTPVerifyResponse', fields={
                    'message': s.CharField(),
                    'access': s.CharField(help_text='JWT access token (expires in 1 hour)'),
                    'refresh': s.CharField(help_text='JWT refresh token (expires in 30 days)'),
                    'user': UserSerializer(),
                }),
                examples=[OpenApiExample('Success', value={
                    'message': 'Login successful',
                    'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    'user': {
                        'id': '550e8400-e29b-41d4-a716-446655440000',
                        'phone_number': '+919876543210',
                        'role': 'customer',
                        'full_name': '',
                        'email': '',
                        'created_at': '2024-01-01T00:00:00Z',
                    },
                })],
            ),
            400: OpenApiResponse(
                description='Invalid or expired OTP',
                response=inline_serializer('OTPVerifyError', fields={
                    'error': s.CharField(),
                    'message': s.CharField(),
                }),
                examples=[OpenApiExample('Wrong OTP', value={
                    'error': 'otp_invalid',
                    'message': 'Invalid OTP. 4 attempt(s) remaining.',
                })],
            ),
        },
        auth=[],
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = OTPService.verify(
                serializer.validated_data['phone_number'],
                serializer.validated_data['otp'],
            )
        except ValueError as e:
            return Response(
                {'error': 'otp_invalid', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tokens = JWTService.issue_tokens(user)
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            **tokens,
        }, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[_TAG],
        summary='Refresh access token',
        description=(
            'Exchange a valid refresh token for a new access token.\n\n'
            '**When to use:** Access token expires after 1 hour. Use this to get a new one without re-entering OTP.\n\n'
            '**Get your refresh token from:** `POST /auth/otp/verify/` response → `refresh` field.'
        ),
        request=inline_serializer('TokenRefreshRequest', fields={
            'refresh': s.CharField(help_text='Your refresh token from /otp/verify/ response'),
        }),
        examples=[
            OpenApiExample(
                'Refresh token example',
                request_only=True,
                value={'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCJ9...'},
            ),
        ],
        responses={
            200: OpenApiResponse(
                description='New access token',
                response=inline_serializer('TokenRefreshResponse', fields={
                    'access': s.CharField(),
                }),
                examples=[OpenApiExample('Success', value={
                    'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                })],
            ),
            401: OpenApiResponse(
                description='Refresh token invalid or expired',
                response=inline_serializer('TokenRefreshError', fields={
                    'error': s.CharField(),
                    'message': s.CharField(),
                }),
            ),
        },
        auth=[],
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'token_missing', 'message': 'Refresh token required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            return Response({'access': str(token.access_token)}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response(
                {'error': 'token_invalid', 'message': str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Get my profile',
        description='Returns the profile of the currently authenticated user.',
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=[_TAG],
        summary='Update my profile',
        description='Update editable fields: `full_name` and `email`. Phone number and role cannot be changed.',
        request=inline_serializer('ProfileUpdateRequest', fields={
            'full_name': s.CharField(required=False, allow_blank=True),
            'email': s.EmailField(required=False, allow_blank=True),
        }),
        responses={200: UserSerializer},
        examples=[
            OpenApiExample('Update name and email', request_only=True, value={
                'full_name': 'Rahul Kumar',
                'email': 'rahul@example.com',
            }),
        ],
    )
    def patch(self, request):
        data = request.data.copy()
        # role can only be set when the user has no role yet (first-time signup)
        if 'role' in data and request.user.role:
            data.pop('role')
        serializer = UserSerializer(request.user, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class LocationUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Update my location',
        description=(
            'Save the user\'s current GPS coordinates.\n\n'
            'Used by the hyperlocal feed to show nearby stores and videos.'
        ),
        request=LocationUpdateSerializer,
        responses={
            200: OpenApiResponse(
                description='Location saved',
                response=inline_serializer('LocationUpdateResponse', fields={
                    'message': s.CharField(),
                }),
                examples=[OpenApiExample('Success', value={'message': 'Location updated'})],
            ),
            400: OpenApiResponse(
                description='Invalid coordinates',
                response=inline_serializer('LocationUpdateError', fields={
                    'latitude': s.ListField(child=s.CharField()),
                }),
                examples=[OpenApiExample('Bad latitude', value={
                    'latitude': ['Ensure this value is less than or equal to 90.']
                })],
            ),
        },
        examples=[
            OpenApiExample('Chennai coordinates', request_only=True, value={
                'latitude': 13.0827,
                'longitude': 80.2707,
            }),
        ],
    )
    def put(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        JWTService.update_location(
            request.user,
            serializer.validated_data['latitude'],
            serializer.validated_data['longitude'],
        )
        return Response({'message': 'Location updated'}, status=status.HTTP_200_OK)

    # Mobile sends PATCH — alias to put so both methods work
    patch = put


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Search user by Profile ID',
        description=(
            'Search for a NearKart user by their Profile ID (e.g. NK-A3X9K2). '
            'Returns name and profile_id only — phone number is never exposed. '
            'Used to find a friend before adding them to a group.'
        ),
        responses={
            200: UserSearchSerializer,
            404: OpenApiResponse(description='No user found with this Profile ID'),
        },
    )
    def get(self, request):
        profile_id = request.query_params.get('profile_id', '').strip().upper()
        if not profile_id:
            return Response({'error': 'missing_param', 'message': 'profile_id query param is required.'}, status=400)
        try:
            from .models import User
            user = User.objects.get(profile_id=profile_id, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'not_found', 'message': 'No user found with this Profile ID.'}, status=404)
        return Response(UserSearchSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Logout',
        description='Blacklists the refresh token so it cannot be reused. Pass your refresh token in the body.',
        request=inline_serializer('LogoutRequest', fields={
            'refresh': s.CharField(help_text='Your refresh token — will be blacklisted'),
        }),
        responses={
            200: OpenApiResponse(
                description='Logged out',
                response=inline_serializer('LogoutResponse', fields={
                    'message': s.CharField(),
                }),
                examples=[OpenApiExample('Success', value={'message': 'Logged out successfully'})],
            ),
        },
        examples=[
            OpenApiExample('Logout', request_only=True, value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
            }),
        ],
    )
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
