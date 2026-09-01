"""
NearKart — Auth Views
POST /api/v1/auth/otp/send/
POST /api/v1/auth/otp/verify/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/client-logs/
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

from core.logging import log_event
from core.utils.ua_parser import parse_ua, get_client_ip
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

        # Sliding window: 5 OTPs per phone per hour.
        # Admin/master_admin accounts are exempt — they need reliable access.
        # Dev bypass: permanent QA accounts skip rate limiting.
        from django.conf import settings as _s
        from core.utils.cache import CacheService
        from .models import User as _User
        is_dev_bypass = phone_number in getattr(_s, 'DEV_BYPASS_PHONES', set())
        # Rate-limit check runs first; admin bypass DB query only fires when the limit is hit
        if not is_dev_bypass and CacheService.is_rate_limited(
            f'otp:{phone_number}', max_requests=5, window_secs=3600
        ):
            is_admin_bypass = _User.objects.filter(
                phone_number=phone_number, role__in=('admin', 'master_admin')
            ).exists()
            if not is_admin_bypass:
                log_event('security', level='warning', action='otp_rate_limited',
                          phone=phone_number,
                          ip=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')))
                return Response(
                    {'error': 'rate_limited', 'message': 'Too many OTP requests. Please try again later.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        is_signup       = serializer.validated_data.get('is_signup', False)
        delivery_method = serializer.validated_data.get('delivery_method', 'sms')
        if not is_signup:
            # Login flow — reject unknown phone numbers instead of silently creating an account
            from .models import User as _User
            if not _User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {'error': 'not_registered', 'message': 'No account found. Please sign up first.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        OTPService.generate_and_send(phone_number, delivery_method)
        log_event('auth', action='otp_sent', phone=phone_number, is_signup=is_signup,
                  delivery_method=delivery_method)
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

        phone      = serializer.validated_data.get('phone_number', '')
        ip         = get_client_ip(request)
        ua_string  = request.META.get('HTTP_USER_AGENT', '')
        ua_parsed  = parse_ua(ua_string)

        # Extra device fields the mobile app can optionally send
        device_name  = request.data.get('device_model', ua_parsed['device_name'])
        os_version   = request.data.get('device_os_version', ua_parsed['os_version'])
        app_version  = request.data.get('app_version', '')
        city         = request.data.get('city', '')

        # OkHttp UA doesn't contain "Android"/"Mobile" — if the app sent
        # device_model it is definitively a mobile device, so override.
        if request.data.get('device_model'):
            ua_parsed['device_type'] = 'mobile'
            if ua_parsed['os'] == 'Unknown':
                ua_parsed['os'] = 'Android'

        def _write_log(user, success, failure_reason=''):
            from .models import UserLoginLog
            try:
                UserLoginLog.objects.create(
                    user=user,
                    phone=str(user.phone_number) if user else phone,
                    role=user.role if user else '',
                    success=success,
                    failure_reason=failure_reason,
                    ip_address=ip or None,
                    city=city or (user.location_city if user else ''),
                    device_type=ua_parsed['device_type'],
                    device_name=device_name or ua_parsed['device_name'],
                    os=ua_parsed['os'],
                    os_version=os_version,
                    browser=ua_parsed['browser'],
                    app_version=app_version,
                    user_agent=ua_string,
                )
            except Exception:
                pass  # logging must never break login

        try:
            user = OTPService.verify(phone, serializer.validated_data['otp'])
        except ValueError as e:
            log_event('security', level='warning', action='login_failed',
                      phone=phone, reason='otp_invalid', ip=ip)
            _write_log(None, success=False, failure_reason='otp_invalid')
            return Response(
                {'error': 'otp_invalid', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_suspended:
            log_event('security', level='warning', action='login_blocked',
                      user_id=str(user.id), phone=str(user.phone_number),
                      reason='account_suspended', ip=ip)
            _write_log(user, success=False, failure_reason='suspended')
            return Response(
                {'error': 'account_suspended', 'message': user.suspension_reason or 'Your account has been temporarily suspended. Please contact support.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Link referral code for new users only
        referral_code = (serializer.validated_data.get('referral_code') or '').strip().upper()
        is_new_user   = user.registered_location is None
        if referral_code and is_new_user:
            try:
                from apps.billing.services import ReferralService
                ReferralService.link_referred_user(user, referral_code)
            except Exception:
                pass

        tokens = JWTService.issue_tokens(user)
        log_event('auth', action='login_success', user_id=str(user.id), role=user.role,
                  phone=str(user.phone_number), is_new=is_new_user, ip=ip,
                  device=ua_parsed['device_type'], os=ua_parsed['os'])
        _write_log(user, success=True)
        return Response({
            'message': 'Login successful',
            'user': UserSerializer(user).data,
            'is_new': is_new_user,
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
        lat  = serializer.validated_data['latitude']
        lng  = serializer.validated_data['longitude']
        city = serializer.validated_data.get('city', '').strip()

        is_first = request.user.registered_location is None
        JWTService.update_location(request.user, lat, lng)

        if city:
            request.user.location_city = city
            request.user.save(update_fields=['location_city'])

        # Option C: one-time NS code area regeneration when city is first set
        if is_first and city:
            code = request.user.profile_id or ''
            segments = code.split('-')
            if len(segments) == 4 and segments[2] == 'XX':
                from core.utils.codes import _area_tag, _random_suffix
                segments[2] = _area_tag(city)
                segments[3] = _random_suffix(4)
                new_code = '-'.join(segments)
                from apps.auth_app.models import User as _User
                while _User.objects.exclude(pk=request.user.pk).filter(profile_id=new_code).exists():
                    segments[3] = _random_suffix(4)
                    new_code = '-'.join(segments)
                request.user.profile_id = new_code
                request.user.save(update_fields=['profile_id'])

        return Response({'message': 'Location updated'}, status=status.HTTP_200_OK)

    # Mobile sends PATCH — alias to put so both methods work
    patch = put


class PopularLocationsView(APIView):
    """Return top 8 most-selected location cities across all users."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Popular locations',
        description='Returns the top 8 most-selected cities by all users.',
        responses={200: inline_serializer('PopularLocationsResponse', fields={
            'results': s.ListField(child=inline_serializer('PopularLocation', fields={
                'city': s.CharField(),
                'count': s.IntegerField(),
            })),
        })},
    )
    def get(self, request):
        from django.db.models import Count
        from .models import User
        cities = (
            User.objects
            .exclude(location_city='')
            .values('location_city')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )
        results = [{'city': row['location_city'], 'count': row['count']} for row in cities]
        return Response({'results': results})


class UserSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=[_TAG],
        summary='Search user by Profile ID',
        description=(
            'Search for a NearSpot user by their Profile ID (e.g. NS-SF-KU-4X2B). '
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
        log_event('auth', action='logout', user_id=str(request.user.id), role=request.user.role)
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class AvatarUploadView(APIView):
    """POST auth/me/avatar/ — upload or replace the user's profile photo."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import uuid, os

        file = request.FILES.get('avatar')
        if not file:
            return Response({'error': 'no_file', 'message': 'Provide an image in the `avatar` field.'}, status=status.HTTP_400_BAD_REQUEST)

        _ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            return Response({'error': 'invalid_file', 'message': 'File must be a valid image (JPEG, PNG, WebP, or GIF).'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from PIL import Image
            import io as _io
            img = Image.open(file)
            img.verify()
            file.seek(0)
        except Exception:
            return Response({'error': 'invalid_file', 'message': 'File must be a valid image.'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(file.name)[1].lower() or '.jpg'
        filename = f'avatars/{request.user.id}/avatar_{uuid.uuid4().hex}{ext}'
        path = default_storage.save(filename, ContentFile(file.read()))
        raw_url = default_storage.url(path)
        if raw_url.startswith('http'):
            avatar_url = raw_url.replace('http://', 'https://', 1)
        else:
            avatar_url = request.build_absolute_uri(raw_url).replace('http://', 'https://', 1)

        request.user.avatar = avatar_url
        request.user.save(update_fields=['avatar'])
        log_event('auth', action='avatar_uploaded', user_id=str(request.user.id))
        return Response({'avatar': avatar_url})


class SessionListView(APIView):
    """
    GET  /auth/me/sessions/  — last 20 successful login sessions for the current user
    DELETE /auth/me/sessions/ — sign out all devices (blacklist current refresh token)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import UserLoginLog
        logs = (
            UserLoginLog.objects
            .filter(user=request.user, success=True)
            .order_by('-created_at')[:20]
        )
        results = [
            {
                'id':          str(log.id),
                'device_type': log.device_type,
                'device_name': log.device_name or 'Unknown device',
                'os':          log.os or '',
                'browser':     log.browser or '',
                'city':        log.city or '',
                'created_at':  log.created_at,
            }
            for log in logs
        ]
        return Response({'results': results})

    def delete(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        log_event('auth', action='signout_all_devices', user_id=str(request.user.id))
        return Response({'message': 'Signed out of all devices successfully'})


class AccountDeleteView(APIView):
    """DELETE /auth/me/ — GDPR right-to-be-forgotten: anonymise and deactivate the account."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        import uuid as _uuid

        # Blacklist current refresh token so it cannot be reused
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        # Anonymise personal data
        anon_suffix = _uuid.uuid4().hex[:12]
        user.phone_number = f'+00{anon_suffix}'
        user.full_name    = 'Deleted User'
        user.email        = ''
        user.avatar       = ''
        user.is_active    = False
        user.save(update_fields=['phone_number', 'full_name', 'email', 'avatar', 'is_active', 'updated_at'])

        # Remove sensitive linked data
        from .models import OTPToken, DeviceToken, SocialAccount
        OTPToken.objects.filter(user=user).delete()
        DeviceToken.objects.filter(user=user).delete()
        SocialAccount.objects.filter(user=user).delete()

        log_event('auth', action='account_deleted', user_id=str(user.id))
        return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class SocialGoogleView(APIView):
    """
    POST /auth/social/google/
    Body: { "id_token": "<Google ID token from client>" }
    Verifies the token with Google, then finds-or-creates a NearSpot user and issues JWT.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        import requests as http_requests
        from django.conf import settings as _s

        id_token_str = request.data.get('id_token', '').strip()
        if not id_token_str:
            return Response({'error': 'id_token_required', 'message': 'id_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify token with Google's tokeninfo endpoint
        try:
            resp = http_requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': id_token_str},
                timeout=10,
            )
            if resp.status_code != 200:
                raise ValueError('Token verification failed')
            info = resp.json()
            if 'error_description' in info:
                raise ValueError(info['error_description'])
        except Exception as e:
            return Response({'error': 'invalid_token', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Validate audience (optional but recommended when GOOGLE_CLIENT_IDS is set)
        allowed_audiences = getattr(_s, 'GOOGLE_CLIENT_IDS', [])
        if allowed_audiences and info.get('aud') not in allowed_audiences:
            return Response({'error': 'invalid_audience', 'message': 'Token audience mismatch.'}, status=status.HTTP_400_BAD_REQUEST)

        google_uid = info.get('sub', '')
        email      = info.get('email', '')
        name       = info.get('name', '')
        picture    = info.get('picture', '')

        if not google_uid:
            return Response({'error': 'invalid_token', 'message': 'Could not extract user ID from token.'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import User as _User, SocialAccount

        # Find existing social account
        try:
            social  = SocialAccount.objects.select_related('user').get(provider='google', provider_uid=google_uid)
            user    = social.user
            is_new  = False
            # Keep extra_data fresh
            social.extra_data = {'email': email, 'name': name, 'picture': picture}
            social.save(update_fields=['extra_data', 'updated_at'])
        except SocialAccount.DoesNotExist:
            # Try to match by verified email
            user = None
            if email:
                user = _User.objects.filter(email=email, is_active=True).first()

            if user is None:
                import uuid as _uuid
                user = _User.objects.create_user(
                    phone_number=f'g_{_uuid.uuid4().hex[:12]}',
                    role='',
                    full_name=name,
                    email=email,
                )
                if picture:
                    user.avatar = picture
                    user.save(update_fields=['avatar'])

            SocialAccount.objects.create(
                user=user,
                provider='google',
                provider_uid=google_uid,
                extra_data={'email': email, 'name': name, 'picture': picture},
            )
            is_new = not user.role

        if not user.is_active:
            return Response({'error': 'account_inactive', 'message': 'This account is no longer active.'}, status=status.HTTP_403_FORBIDDEN)

        tokens = JWTService.issue_tokens(user)
        log_event('auth', action='social_login', provider='google', user_id=str(user.id), is_new=is_new)
        return Response({
            'message': 'Login successful',
            'user':    UserSerializer(user).data,
            'is_new':  is_new,
            **tokens,
        }, status=status.HTTP_200_OK)


class ClientLogsView(APIView):
    """
    Receives security events shipped from the mobile app (login_failed,
    login_blocked, etc.) and writes them to security.log with full device context.

    No auth required — events are often sent before a token exists (e.g. login failures).
    Accepts maximum 50 events per request to prevent abuse.
    """
    permission_classes = [AllowAny]

    _ALLOWED_ACTIONS = frozenset({
        'login_failed', 'login_blocked', 'otp_rate_limited',
    })

    def post(self, request):
        events = request.data.get('events', [])
        if not isinstance(events, list):
            return Response({'error': 'events must be a list'}, status=400)

        written = 0
        for event in events[:50]:
            action = event.get('action', '')
            if action not in self._ALLOWED_ACTIONS:
                continue
            ALLOWED_EXTRA_KEYS = {'screen', 'action', 'platform', 'version', 'os'}
            extra = {k: v for k, v in event.get('extra', {}).items()
                     if k in ALLOWED_EXTRA_KEYS and isinstance(v, str)}
            log_event(
                'client_events',
                level        = 'warning',
                action       = action,
                install_id   = event.get('install_id', ''),
                device_model = event.get('device_model', ''),
                os_version   = event.get('os_version', ''),
                app_version  = event.get('app_version', ''),
                network_type = event.get('network_type', ''),
                ip           = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')),
                **extra,
            )
            written += 1

        return Response({'written': written}, status=status.HTTP_200_OK)
