#!/bin/bash
# ============================================================
# NearKart — GitHub Issues Creator
# Run this script once inside your nearkart-backend repo
# REQUIRES: GitHub CLI (gh) installed and authenticated
# USAGE: chmod +x create_nearkart_issues.sh && ./create_nearkart_issues.sh
# ============================================================

set -e
echo "🚀 Creating NearKart Sprint Labels..."

# Create labels
gh label create "Sprint-0" --color "6B7280" --description "Environment Setup" 2>/dev/null || true
gh label create "Sprint-1" --color "3B82F6" --description "Django Foundation" 2>/dev/null || true
gh label create "Sprint-2" --color "10B981" --description "Auth Module" 2>/dev/null || true
gh label create "Sprint-3" --color "F59E0B" --description "Store + Product Module" 2>/dev/null || true
gh label create "Sprint-4" --color "8B5CF6" --description "Video Module" 2>/dev/null || true
gh label create "Sprint-5" --color "EC4899" --description "Chat WebSocket" 2>/dev/null || true
gh label create "Sprint-6" --color "EF4444" --description "Blacklist Engine" 2>/dev/null || true
gh label create "Sprint-7" --color "F97316" --description "Billing + Wallet + Reservations" 2>/dev/null || true
gh label create "Sprint-8" --color "14B8A6" --description "Analytics + Admin + Docs" 2>/dev/null || true
gh label create "Sprint-9" --color "6366F1" --description "Customer Mobile App" 2>/dev/null || true
gh label create "Sprint-10" --color "84CC16" --description "Vendor Mobile App" 2>/dev/null || true
gh label create "Sprint-11" --color "0EA5E9" --description "Vendor Web Dashboard" 2>/dev/null || true
gh label create "Sprint-12" --color "D946EF" --description "Staging + UAT + Production" 2>/dev/null || true
gh label create "Backend" --color "1E40AF" --description "Backend task" 2>/dev/null || true
gh label create "Mobile" --color "F97316" --description "Mobile task" 2>/dev/null || true
gh label create "DevOps" --color "059669" --description "DevOps / Infrastructure" 2>/dev/null || true
gh label create "Blocked" --color "DC2626" --description "Blocked task" 2>/dev/null || true

echo "✅ Labels created!"
echo ""
echo "📋 Creating Sprint 0 — Environment Setup (16 tasks)..."

gh issue create --title "S0-T01 — Install Python 3.11+" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing — start here

**Task:**
Install Python 3.11.x on your machine.

**Done When:**
\`\`\`
python --version
# Shows: Python 3.11.x
\`\`\`

**Notes:** Use python3 on macOS. On Windows tick 'Add Python to PATH' during install."

gh issue create --title "S0-T02 — Install Node.js 18+ and npm" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Task:**
Install Node.js 18 LTS from nodejs.org

**Done When:**
\`\`\`
node --version   # v18.x.x
npm --version    # 9.x.x
\`\`\`"

gh issue create --title "S0-T03 — Install Docker Desktop" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 1h
**Depends:** Nothing

**Task:**
Install Docker Desktop. Runs all 6 NearKart services locally.

**Services it will run:**
- django:8000
- celery-worker
- celery-beat
- postgres (postgis):5432
- redis:7-alpine
- nginx:80

**Done When:**
\`\`\`
docker --version           # Docker 24.x.x
docker-compose --version   # Docker Compose 2.x.x
\`\`\`"

gh issue create --title "S0-T04 — Install Git and configure name and email" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Task:**
Install Git and configure identity.

**Commands:**
\`\`\`
git config --global user.name 'Your Name'
git config --global user.email 'your@email.com'
\`\`\`

**Done When:**
\`\`\`
git --version   # git version 2.x.x
\`\`\`"

gh issue create --title "S0-T05 — Install VS Code and extensions" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Required Extensions:**
- Python (Microsoft)
- Pylance (Microsoft)
- Django (Baptiste Darthenay)
- ESLint (Microsoft)
- Prettier
- Docker (Microsoft)
- GitLens
- REST Client
- DotENV"

gh issue create --title "S0-T06 — Install Postman for API testing" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Task:**
Install Postman from postman.com. Create NearKart Local environment with base_url=http://localhost:8000"

gh issue create --title "S0-T07 — Create GitHub repo nearkart-backend" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** S0-T04

**Task:**
Create private GitHub repo: nearkart-backend

**Branches:**
- main (production)
- develop (active development)

**Notes:** Extract backend starter ZIP and push to develop branch."

gh issue create --title "S0-T08 — Create GitHub repo nearkart-mobile" \
  --label "Sprint-0,Mobile" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** S0-T04

**Task:**
Create private GitHub repo: nearkart-mobile

**Branches:**
- main
- develop

**Notes:** No files to push yet. Mobile code starts in Sprint 9."

gh issue create --title "S0-T09 — Create AWS account and enable MFA" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 1h
**Depends:** Nothing

**Task:**
Create AWS account. Enable MFA immediately on root account.

**Notes:** Use Free Tier. Region: ap-south-1 (Mumbai)"

gh issue create --title "S0-T10 — Create AWS IAM user nearkart-dev" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** S0-T09

**Permissions needed:**
- S3
- EC2
- RDS
- CloudFront
- SecretsManager"

gh issue create --title "S0-T11 — Create AWS S3 bucket nearkart-media-dev" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** S0-T09

**Settings:**
- Region: ap-south-1
- SSE-S3 encryption: ON
- Public access: BLOCKED"

gh issue create --title "S0-T12 — Create Firebase project and enable FCM" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 1h
**Depends:** Nothing

**Task:**
Create Firebase project. Enable FCM for push notifications.

**Downloads needed:**
- google-services.json (Android)
- GoogleService-Info.plist (iOS)"

gh issue create --title "S0-T13 — Create Twilio account for SMS OTP" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Credentials to save:**
- Account SID
- Auth Token
- Phone number"

gh issue create --title "S0-T14 — Create Google Cloud and enable Maps APIs" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 1h
**Depends:** Nothing

**Enable these APIs:**
- Maps JavaScript API
- Places API
- Geocoding API
- Directions API"

gh issue create --title "S0-T15 — Create Sentry project nearkart-backend" \
  --label "Sprint-0,DevOps" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Task:**
Create Sentry project. Get DSN URL for Django settings."

gh issue create --title "S0-T16 — Create SendGrid account and API key" \
  --label "Sprint-0,Backend" \
  --body "**Sprint:** 0 — Environment Setup
**Time:** 0.5h
**Depends:** Nothing

**Task:**
Create SendGrid account. Verify sender domain for email deliverability."

echo "✅ Sprint 0 done! (16 issues)"
echo ""
echo "📋 Creating Sprint 1 — Django Foundation (14 tasks)..."

gh issue create --title "S1-T01 — Create Django project folder structure" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 2h
**Depends:** S0-T01, S0-T03, S0-T07

**Structure:**
- config/ (settings, urls, asgi, wsgi, celery)
- apps/ (13 Django apps)
- core/ (utils, models, exceptions, permissions, pagination)
- requirements/ (base, dev, prod)
- docker-compose.yml, Dockerfile, .env.example, pytest.ini"

gh issue create --title "S1-T02 — Write requirements/base.txt" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T01

**Key packages:**
django==4.2.13, djangorestframework, psycopg2-binary, channels, celery, redis, boto3, firebase-admin, twilio, sendgrid, drf-spectacular, sentry-sdk"

gh issue create --title "S1-T03 — Write docker-compose.yml" \
  --label "Sprint-1,DevOps" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 1h
**Depends:** S1-T01

**Services:**
- django:8000
- celery-worker
- celery-beat
- postgres (postgis:15-3.3):5432
- redis:7-alpine
- nginx"

gh issue create --title "S1-T04 — Write Dockerfile multi-stage build" \
  --label "Sprint-1,DevOps" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 1h
**Depends:** S1-T01

**Stages:**
- Stage 1 (builder): install libgdal libgeos ffmpeg gcc pip-install
- Stage 2 (production): copy site-packages only, non-root appuser"

gh issue create --title "S1-T05 — Write .env.example with all variables" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T01

**Variable groups:**
SECRET_KEY, DEBUG, DB_*, REDIS_URL, AWS_*, JWT_*, TWILIO_*, FIREBASE_*, SENDGRID_*, GOOGLE_MAPS_*, SENTRY_*"

gh issue create --title "S1-T06 — Write config/settings/base.py" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 2h
**Depends:** S1-T02, S1-T05

**Key settings:**
- All 13 apps + django.contrib.gis
- DATABASES postgis backend
- CHANNEL_LAYERS Redis
- CACHES Redis
- CELERY Asia/Kolkata timezone
- JWT: 1hr access, 30d refresh
- CORS, DRF, Sentry"

gh issue create --title "S1-T07 — Write core/models.py BaseModel" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T06

**Fields:**
- id: UUID PK
- created_at: auto_now_add
- updated_at: auto_now
- abstract=True
- ordering: -created_at"

gh issue create --title "S1-T08 — Write core/exceptions.py custom handler" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 1h
**Depends:** S1-T07

**Handles:**
ValidationError, AuthenticationFailed, PermissionDenied, NotFound

**Format:** { error, message, code, details }"

gh issue create --title "S1-T09 — Write core/permissions.py" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T07

**Classes:**
IsCustomer, IsVendor, IsAdmin, IsStoreOwner (object-level)"

gh issue create --title "S1-T10 — Write core/pagination.py" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T07

**Classes:**
- StandardCursorPagination (video feed)
- StandardOffsetPagination (product lists)"

gh issue create --title "S1-T11 — Write nginx.conf" \
  --label "Sprint-1,DevOps" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 1h
**Depends:** S1-T03

**Config:**
- Rate limits: api 60/min, otp 5/hr
- proxy_pass /api/ → django:8000
- proxy_pass /ws/ → daphne:8001 with WebSocket upgrade headers"

gh issue create --title "S1-T12 — Run docker-compose up and verify all services" \
  --label "Sprint-1,DevOps" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 1h
**Depends:** S1-T03, S1-T04, S1-T06

**Done When:**
All 6 containers healthy: django, celery, celery-beat, postgres, redis, nginx"

gh issue create --title "S1-T13 — Run migrations and verify PostGIS extension" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T12

**Commands:**
\`\`\`
docker exec nearkart-django python manage.py migrate
\`\`\`

**Verify:**
\`\`\`sql
SELECT PostGIS_Version();
\`\`\`"

gh issue create --title "S1-T14 — Create Django superuser and verify admin panel" \
  --label "Sprint-1,Backend" \
  --body "**Sprint:** 1 — Django Foundation
**Time:** 0.5h
**Depends:** S1-T13

**Done When:**
http://localhost:8000/admin/ loads and login works"

echo "✅ Sprint 1 done! (14 issues)"
echo ""
echo "📋 Creating Sprint 2 — Auth Module (7 tasks)..."

gh issue create --title "S2-T01 — Create User OTPToken UserLocation DeviceToken models" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 2.25h
**Depends:** S1-T07, S1-T13

**Models:**
- User: extends AbstractBaseUser, phone_number UNIQUE IDX, role enum (customer/vendor/admin), registered_location PointField SRID4326 GIST index
- OTPToken: otp_hash sha256, expires_at, is_used, attempts max 5
- DeviceToken: fcm_token UNIQUE(user, fcm_token)"

gh issue create --title "S2-T02 — Write auth_app/services.py OTPService JWTService" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 3h
**Depends:** S2-T01

**OTPService.generate_and_send:** invalidate old OTPs, generate 6-digit, sha256-hash, queue SMS task
**OTPService.verify:** find latest, compare sha256, increment attempts, lock at 5
**JWTService.issue_tokens:** embed role+phone claims, return access(1hr)+refresh(30d)"

gh issue create --title "S2-T03 — Write notifications/services.py SMSService" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 1h
**Depends:** S2-T01

**SMSService.send_otp(phone, otp)** via Twilio REST API"

gh issue create --title "S2-T04 — Write auth_app/tasks.py and serializers.py" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 1.5h
**Depends:** S2-T02, S2-T03

**Task:** send_otp_sms.delay(phone, otp)
**Serializers:** OTPSendSerializer (+91 validation), OTPVerifySerializer (6-digits), UserSerializer, LocationUpdateSerializer"

gh issue create --title "S2-T05 — Write auth_app/views.py and urls.py" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 2.5h
**Depends:** S2-T02, S2-T04

**Views:**
- OTPSendView (5/hr/phone rate limit)
- OTPVerifyView (10/hr/IP)
- TokenRefreshView, MeView, LocationUpdateView, LogoutView

**URL prefix:** /api/v1/auth/"

gh issue create --title "S2-T06 — Write core/middleware.py JWT auth for WebSocket" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 1h
**Depends:** S2-T02

**JWTAuthMiddleware:**
- parse_qs to get token
- AccessToken decode
- scope[user] = user or None if invalid"

gh issue create --title "S2-T07 — Write tests and test in Postman" \
  --label "Sprint-2,Backend" \
  --body "**Sprint:** 2 — Auth Module
**Time:** 3h
**Depends:** S2-T05

**Tests:**
- OTP send 200, 6th attempt 429
- Verify success, wrong OTP 400, expired 400
- /me with token 200, without token 401

**Postman:** Real SMS received, tokens work"

echo "✅ Sprint 2 done! (7 issues)"
echo ""
echo "📋 Creating Sprint 3 — Store + Product Module (6 tasks)..."

gh issue create --title "S3-T01 — Create Store StoreHours StoreFollow StoreReview models" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 2.5h
**Depends:** S2-T01, S1-T13

**Store model:**
- owner: OneToOne
- name: GIN index
- location: GIST index SRID4326
- category: enum
- is_verified, is_active, is_open
- performance_score, wallet_balance
- COMPOSITE index (is_active, is_verified)

**StoreHours:** day 0-6, UNIQUE(store, day)
**StoreFollow, StoreReview:** UNIQUE(user, store)"

gh issue create --title "S3-T02 — Create Product ProductVariant ProductImage Wishlist models" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 2.5h
**Depends:** S3-T01

**Product:**
- store FK, name GIN index
- status enum, is_visible IDX (blacklist flag)
- last_updated_at B-tree IDX (30d timer)
- COMPOSITE(status, is_visible)

**ProductVariant:** stock_quantity B-tree IDX (blacklist trigger)
**Wishlist:** UNIQUE(user, product)"

gh issue create --title "S3-T03 — Write core/utils/geo.py and core/utils/cache.py" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 2h
**Depends:** S3-T01, S3-T02

**geo.py:**
- get_nearby_stores: Point + Distance + annotate
- get_nearby_products: same + is_visible + stock>0
- reverse_geocode via Google Maps

**cache.py:**
- Keys round lat/lng to 3 decimals
- Delete/invalidation functions
- TTL: 300s for nearby stores, 120s for video feed"

gh issue create --title "S3-T04 — Write stores/services.py and products/services.py" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 5h
**Depends:** S3-T01, S3-T02, S3-T03

**GeoService:** Redis TTL 300s → PostGIS → SET Redis
**StoreService:** create, update, update_is_open
**QRService:** generate → S3 → CDN URL
**ProductService:** create, update, get_nearby, search (pg_trgm), wishlist"

gh issue create --title "S3-T05 — Write serializers views URLs for stores and products" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 4h
**Depends:** S3-T04

**Store endpoints:**
- GET /stores/nearby, /stores/:id
- POST /stores, PUT /:id, follow, qr-code

**Product endpoints:**
- GET /products/nearby, /search, /products/:id, variants
- POST /products, PUT/DELETE /products/:id, wishlist, reserve"

gh issue create --title "S3-T06 — Write tests and test in Postman" \
  --label "Sprint-3,Backend" \
  --body "**Sprint:** 3 — Store + Product Module
**Time:** 3.5h
**Depends:** S3-T05

**Tests:**
- Distance sorted correctly
- Only visible products returned
- Radius filter works
- Category filter works
- 401 without token

**Postman:** GET /stores/nearby with real lat/lng coordinates"

echo "✅ Sprint 3 done! (6 issues)"
echo ""
echo "📋 Creating Sprint 4 — Video Module (6 tasks)..."

gh issue create --title "S4-T01 — Create Video VideoProductTag VideoLike models" \
  --label "Sprint-4,Backend" \
  --body "**Sprint:** 4 — Video Module
**Time:** 1.75h
**Depends:** S3-T01, S3-T02

**Video model:**
- type enum, status enum
- s3_key, hls_manifest_url, thumbnail_url
- reach_radius_km: 1-5
- is_pinned
- expires_at: B-tree IDX
- COMPOSITE(status, expires_at)
- Auto-set: +30d regular, +24h story on create

**VideoProductTag:** position_x, position_y (float 0-1)"

gh issue create --title "S4-T02 — Write core/utils/s3.py" \
  --label "Sprint-4,Backend" \
  --body "**Sprint:** 4 — Video Module
**Time:** 1h
**Depends:** S0-T10, S0-T11

**Functions:**
- generate_presigned_upload_url: boto3 put_object, ExpiresIn=900, key=videos/storeId/videoId/original.mp4
- delete_video_files: list + delete all under prefix
- upload_image: return CDN URL"

gh issue create --title "S4-T03 — Write videos/tasks.py transcode and delete expired" \
  --label "Sprint-4,Backend" \
  --body "**Sprint:** 4 — Video Module
**Time:** 3h
**Depends:** S4-T01, S4-T02

**transcode_video task:**
download → FFmpeg 360p@400k, 720p@1500k, 1080p@3000k HLS (hls_time=4) → thumbnail -ss 1s scale=480x270 → upload all to S3 → status=active

**delete_expired_videos:** Celery Beat 1am daily, query + delete + notify vendor"

gh issue create --title "S4-T04 — Write videos services serializers views URLs" \
  --label "Sprint-4,Backend" \
  --body "**Sprint:** 4 — Video Module
**Time:** 4.5h
**Depends:** S4-T01, S4-T02, S4-T03

**FeedService:** Redis check → PostGIS ST_DWithin reach_radius_km → cache 120s
**Feeds:** get_following, get_trending

**Endpoints:**
upload (presigned), s3-webhook (transcode trigger), feed, feed/following, feed/trending, pin, delete, like"

gh issue create --title "S4-T05 — Configure S3 event notification to webhook" \
  --label "Sprint-4,DevOps" \
  --body "**Sprint:** 4 — Video Module
**Time:** 1h
**Depends:** S0-T11, S4-T04

**Config:**
S3 ObjectCreated → filter prefix: videos/, suffix: original.mp4 → HTTP POST /api/v1/videos/s3-webhook/"

gh issue create --title "S4-T06 — Test video pipeline end-to-end" \
  --label "Sprint-4,Backend" \
  --body "**Sprint:** 4 — Video Module
**Time:** 2h
**Depends:** S4-T04, S4-T05

**Full flow:**
upload → presigned URL → S3 → webhook fires → Celery task → FFmpeg → HLS segments → status=active → feed API returns video"

echo "✅ Sprint 4 done! (6 issues)"
echo ""
echo "📋 Creating Sprint 5 — Chat WebSocket (6 tasks)..."

gh issue create --title "S5-T01 — Create Conversation Message models" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 1.25h
**Depends:** S3-T01, S3-T02

**Conversation:** customer+store FK, product FK null, last_message_at, UNIQUE(customer, store)
**Message:** conversation FK, sender FK, content, is_read, delivered_at, read_at, ordering: created_at ASC"

gh issue create --title "S5-T02 — Configure ASGI in config/asgi.py" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 1h
**Depends:** S1-T06, S2-T06

**Config:**
ProtocolTypeRouter: http → wsgi, websocket → AllowedHostsOriginValidator(JWTAuthMiddlewareStack(URLRouter(patterns)))"

gh issue create --title "S5-T03 — Write chat/consumers.py ChatConsumer" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 3h
**Depends:** S5-T01, S5-T02

**connect:** JWT check, access check, group_add, presence SET, accept
**disconnect:** group_discard, presence DEL
**receive (message type):** save message, group_send, check presence → FCM if offline
**receive (read_receipt type):** mark read, group_send"

gh issue create --title "S5-T04 — Write notifications/services.py FCM SMS Email" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 2h
**Depends:** S0-T12, S0-T13, S0-T16

**PushService:** send_push, notify_blacklist, notify_restock, notify_new_video
**EmailService:** blacklist_warning, approval, weekly_digest"

gh issue create --title "S5-T05 — Write chat views serializers routing URLs" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 1.75h
**Depends:** S5-T01, S5-T03

**REST:**
- GET/POST /conversations
- GET/POST /conversations/:id/messages
- POST /broadcast

**WebSocket:** ws/chat/{conv_id}/"

gh issue create --title "S5-T06 — Test WebSocket in Postman" \
  --label "Sprint-5,Backend" \
  --body "**Sprint:** 5 — Chat WebSocket
**Time:** 1.5h
**Depends:** S5-T03

**Tests:**
- Connect with valid JWT → 101 Switching Protocols
- Connect with invalid JWT → close 4001
- Message received instantly
- Read receipt works
- Disconnect → presence removed from Redis"

echo "✅ Sprint 5 done! (6 issues)"
echo ""
echo "📋 Creating Sprint 6 — Blacklist Engine (6 tasks)..."

gh issue create --title "S6-T01 — Create BlacklistLog model" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 0.75h
**Depends:** S3-T02

**Fields:**
- product FK
- reason enum: inactive_30d / out_of_stock
- triggered_by enum: time / stock
- resolved_at: null until reactivated"

gh issue create --title "S6-T02 — Write blacklist/services.py BlacklistService" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 3h
**Depends:** S3-T02, S5-T04

**check_time_based:**
- Day 20-26: WARNING notification
- Day 27-29: FINAL WARNING notification
- Day 30+: BLACKLIST → is_visible=False

**check_stock_based:**
- All variants stock=0 → hide immediately

**reactivate:** clear fields, notify wishlist customers
**_hide_product:** is_visible=False, push+email vendor"

gh issue create --title "S6-T03 — Write blacklist/tasks.py" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 1h
**Depends:** S6-T02

**Tasks:**
- check_inactive_products → calls check_time_based
- check_product_stock(product_id) → calls check_stock_based"

gh issue create --title "S6-T04 — Add post_save signal on ProductVariant" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 0.5h
**Depends:** S6-T03, S3-T02

**Signal:**
post_save(ProductVariant) → check_product_stock.delay(instance.product_id)"

gh issue create --title "S6-T05 — Wire ALL Celery Beat schedules" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 1h
**Depends:** S6-T03, S4-T03

**Schedules:**
- Midnight: check_inactive_products
- 1am: delete_expired_videos
- 3am: aggregate_daily_stats
- Every 15min: expire_reservations
- Every 30min: update_store_open
- Monday 9am: weekly_digest"

gh issue create --title "S6-T06 — Test both blacklist triggers and reactivation" \
  --label "Sprint-6,Backend" \
  --body "**Sprint:** 6 — Blacklist Engine
**Time:** 3h
**Depends:** S6-T04, S6-T05

**Test 1 (time trigger):** Set last_updated_at to 31 days ago → run task → is_visible=False ✅
**Test 2 (stock trigger):** Set stock=0 → signal fires → product hidden ✅
**Test 3 (reactivation):** Update product → is_visible=True → wishlist customers notified ✅"

echo "✅ Sprint 6 done! (6 issues)"
echo ""
echo "📋 Creating Sprint 7 — Billing + Wallet + Reservations (4 tasks)..."

gh issue create --title "S7-T01 — Create Invoice WalletTransaction Expense Reservation models" \
  --label "Sprint-7,Backend" \
  --body "**Sprint:** 7 — Billing + Wallet + Reservations
**Time:** 2.5h
**Depends:** S3-T01, S3-T02

**Invoice:** invoice_number UNIQUE (NK-YYYY-NNNNN), items JSONB, total_amount, pdf_url
**WalletTransaction:** type enum, amount, balance_after (audit trail)
**Reservation:** status enum, expires_at: NOW+2hr"

gh issue create --title "S7-T02 — Write billing services InvoiceService WalletService ReferralService" \
  --label "Sprint-7,Backend" \
  --body "**Sprint:** 7 — Billing + Wallet + Reservations
**Time:** 3h
**Depends:** S7-T01

**InvoiceService:** auto-number, generate_pdf via reportlab → S3
**WalletService:** credit (update balance + create WalletTx), debit (check sufficient, raise if not)
**ReservationService:** expire reservations Celery every 15min"

gh issue create --title "S7-T03 — Write billing reservation serializers views URLs" \
  --label "Sprint-7,Backend" \
  --body "**Sprint:** 7 — Billing + Wallet + Reservations
**Time:** 3h
**Depends:** S7-T02

**Billing endpoints:**
- POST/GET /invoices
- GET /:id/pdf
- GET /wallet/balance + transactions
- POST /referral/apply
- GET/POST /expenses

**Reservation endpoints:**
- POST /reservations
- PUT /:id/confirm
- PUT /:id/cancel"

gh issue create --title "S7-T04 — Test billing wallet reservation flows" \
  --label "Sprint-7,Backend" \
  --body "**Sprint:** 7 — Billing + Wallet + Reservations
**Time:** 2h
**Depends:** S7-T03

**Tests:**
- Invoice → PDF generated → URL returned ✅
- Wallet credit → balance increases ✅
- Wallet debit insufficient → 400 error ✅
- Reserve product → expires_at set → 15min Celery task cancels expired ✅"

echo "✅ Sprint 7 done! (4 issues)"
echo ""
echo "📋 Creating Sprint 8 — Analytics + Admin + Docs (5 tasks)..."

gh issue create --title "S8-T01 — Create StoreView ProductView VideoView models" \
  --label "Sprint-8,Backend" \
  --body "**Sprint:** 8 — Analytics + Admin + Docs
**Time:** 1h
**Depends:** S3-T01, S3-T02, S4-T01

**Models:**
StoreView, ProductView, VideoView:
- object FK, viewer FK (null), date, device_type"

gh issue create --title "S8-T02 — Write analytics services and tasks" \
  --label "Sprint-8,Backend" \
  --body "**Sprint:** 8 — Analytics + Admin + Docs
**Time:** 3h
**Depends:** S8-T01

**AnalyticsService:** overview, products, videos, peak_hours, export_pdf
**Task:** aggregate_daily_stats (3am)
**Task:** send_weekly_digest (Monday 9am)"

gh issue create --title "S8-T03 — Write analytics and admin views serializers URLs" \
  --label "Sprint-8,Backend" \
  --body "**Sprint:** 8 — Analytics + Admin + Docs
**Time:** 3h
**Depends:** S8-T02

**Analytics endpoints:**
overview, products, videos, peak-hours, export

**Admin endpoints:**
vendors/pending, vendors/:id/approve, blacklist/overview, platform/stats, announcements"

gh issue create --title "S8-T04 — Configure drf-spectacular Swagger UI" \
  --label "Sprint-8,Backend" \
  --body "**Sprint:** 8 — Analytics + Admin + Docs
**Time:** 1h
**Depends:** S1-T06

**Config:**
- SPECTACULAR_SETTINGS in base.py
- @extend_schema decorators on all views
- /api/docs/ → Swagger UI
- /api/schema/ → OpenAPI JSON"

gh issue create --title "S8-T05 — Run pytest suite and verify 75% coverage" \
  --label "Sprint-8,Backend" \
  --body "**Sprint:** 8 — Analytics + Admin + Docs
**Time:** 2h
**Depends:** S8-T03

**Command:**
\`\`\`
pytest --cov=apps tests/ -v
\`\`\`

**Done When:**
- 75%+ test coverage ✅
- /api/docs/ shows all endpoints ✅"

echo "✅ Sprint 8 done! (5 issues)"
echo ""
echo "📋 Creating Sprint 9 — Customer Mobile App (10 tasks)..."

gh issue create --title "S9-T01 — Setup React Native Expo project" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 2h
**Depends:** S0-T02

**Command:**
\`\`\`
npx create-expo-app nearkart-mobile
\`\`\`

**Install:**
@react-navigation, zustand, axios, expo-av, expo-location, react-native-maps"

gh issue create --title "S9-T02 — Setup navigation AuthStack MainStack" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 2h
**Depends:** S9-T01

**AuthStack:** Phone → OTP → RoleSelect → Location
**MainStack BottomTabs:** Home | VideoFeed | Map | Chat | Profile"

gh issue create --title "S9-T03 — Setup Zustand stores and Axios API client" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 2.5h
**Depends:** S9-T01

**Stores:** authStore, locationStore, feedStore
**Axios:** base URL, JWT header injection, 401 refresh-retry interceptor"

gh issue create --title "S9-T04 — Build OTP Login flow (4 screens)" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 3h
**Depends:** S9-T02, S9-T03

**Screens:**
1. Phone number entry
2. OTP input (6 boxes, 5min timer)
3. Role selection (Customer/Vendor)
4. Location capture"

gh issue create --title "S9-T05 — Build Customer Home Feed screen" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 4h
**Depends:** S9-T03

**Features:**
- Radius slider
- Category pills
- Store cards
- Product grid with stock status
- Pull-to-refresh
- Infinite scroll (cursor pagination)"

gh issue create --title "S9-T06 — Build Hyperlocal Video Feed screen" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 4h
**Depends:** S9-T03

**Features:**
- Near You / Following / Trending tabs
- Full-screen expo-av HLS player
- Product tag overlay (tap to view product)
- Right-side actions: like, chat, share, save"

gh issue create --title "S9-T07 — Build Chat screen with WebSocket" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 3h
**Depends:** S9-T03, S5-T03

**Features:**
- Conversation list
- Message thread
- WebSocket real-time messages
- Read receipts"

gh issue create --title "S9-T08 — Build Product Detail Map and Wishlist screens" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 4h
**Depends:** S9-T03

**Product screen:** gallery, variants, stock, reserve, chat
**Map screen:** Google Maps with store pins"

gh issue create --title "S9-T09 — Integrate FCM push notifications" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 2h
**Depends:** S0-T12, S9-T01

**Handle:**
- Register device token
- Foreground notifications
- Background notifications
- Terminated app notifications"

gh issue create --title "S9-T10 — Test customer app on Android and iOS" \
  --label "Sprint-9,Mobile" \
  --body "**Sprint:** 9 — Customer Mobile App
**Time:** 3h
**Depends:** S9-T09

**Full flow test:**
Login → Discover stores → Watch video → Open chat → Reserve product"

echo "✅ Sprint 9 done! (10 issues)"
echo ""
echo "📋 Creating Sprint 10 — Vendor Mobile App (5 tasks)..."

gh issue create --title "S10-T01 — Vendor Dashboard and Store Setup screens" \
  --label "Sprint-10,Mobile" \
  --body "**Sprint:** 10 — Vendor Mobile App
**Time:** 5h
**Depends:** S9-T02, S9-T03

**Dashboard:** KPI strip, quick actions, blacklist alert, activity feed
**Store Setup:** name, category, address, map picker, opening hours, banner image"

gh issue create --title "S10-T02 — Product Management screen" \
  --label "Sprint-10,Mobile" \
  --body "**Sprint:** 10 — Vendor Mobile App
**Time:** 4h
**Depends:** S10-T01

**Features:**
- Product list with blacklist badges
- Add/edit product form
- Variants (size/colour/stock)
- Multi-image upload and reorder"

gh issue create --title "S10-T03 — Video Upload screen" \
  --label "Sprint-10,Mobile" \
  --body "**Sprint:** 10 — Vendor Mobile App
**Time:** 3h
**Depends:** S10-T01

**Features:**
- Record or pick video from gallery
- Caption input
- Radius slider (1–5km)
- Product tag placement (tap on video frame)
- Direct S3 presigned upload with progress bar"

gh issue create --title "S10-T04 — Billing Chat Notifications screens" \
  --label "Sprint-10,Mobile" \
  --body "**Sprint:** 10 — Vendor Mobile App
**Time:** 5h
**Depends:** S10-T01

**Billing:** create invoice, list invoices, PDF download, expense tracker, wallet balance
**Chat:** conversation list, reply to customers
**Notifications:** all vendor alerts (blacklist, restock, new follower)"

gh issue create --title "S10-T05 — Test vendor app on Android and iOS" \
  --label "Sprint-10,Mobile" \
  --body "**Sprint:** 10 — Vendor Mobile App
**Time:** 2h
**Depends:** S10-T04

**Full flow:**
Setup store → Add products → Post video → Create invoice"

echo "✅ Sprint 10 done! (5 issues)"
echo ""
echo "📋 Creating Sprint 11 — Vendor Web Dashboard (5 tasks)..."

gh issue create --title "S11-T01 — Setup React TypeScript Vite project" \
  --label "Sprint-11,Backend" \
  --body "**Sprint:** 11 — Vendor Web Dashboard
**Time:** 1h
**Depends:** S0-T02

**Command:**
\`\`\`
npm create vite@latest nearkart-web -- --template react-ts
\`\`\`

**Install:**
react-router-dom, zustand, axios, recharts, tailwindcss"

gh issue create --title "S11-T02 — Auth layout sidebar and routing" \
  --label "Sprint-11,Backend" \
  --body "**Sprint:** 11 — Vendor Web Dashboard
**Time:** 2h
**Depends:** S11-T01

**Sidebar sections:**
Dashboard | Products | Videos | Billing | Analytics | Staff | Settings"

gh issue create --title "S11-T03 — Analytics Dashboard page" \
  --label "Sprint-11,Backend" \
  --body "**Sprint:** 11 — Vendor Web Dashboard
**Time:** 4h
**Depends:** S11-T02, S8-T03

**Components:**
- KPI cards (vs last period)
- 7-day bar chart
- Category donut chart
- Product performance table
- PDF export button"

gh issue create --title "S11-T04 — Product and Staff Management pages" \
  --label "Sprint-11,Backend" \
  --body "**Sprint:** 11 — Vendor Web Dashboard
**Time:** 3h
**Depends:** S11-T02

**Products:** full table, bulk operations, blacklist filter, inline stock edit
**Staff:** add/remove team members, role assignment, activity log"

gh issue create --title "S11-T05 — Reports Export and cross-browser testing" \
  --label "Sprint-11,Backend" \
  --body "**Sprint:** 11 — Vendor Web Dashboard
**Time:** 3h
**Depends:** S11-T03

**Features:**
- Date range picker
- Revenue and expense reports
- Export PDF and CSV

**Test on:** Chrome, Firefox, Safari"

echo "✅ Sprint 11 done! (5 issues)"
echo ""
echo "📋 Creating Sprint 12 — Staging + UAT + Production (9 tasks)..."

gh issue create --title "S12-T01 — Setup AWS ECS ECR ALB for Django" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 3h
**Depends:** S0-T09, S8-T05

**Setup:**
- ECS cluster
- Task definition: Django + Celery + Beat
- ECR repository
- Application Load Balancer
- Target groups and security groups"

gh issue create --title "S12-T02 — Setup AWS RDS PostgreSQL with PostGIS" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 2h
**Depends:** S0-T09

**Config:**
- Instance: db.t3.micro
- Region: ap-south-1
- Enable PostGIS extension
- Automated backups: 7 days"

gh issue create --title "S12-T03 — Setup ElastiCache Redis and CloudFront CDN" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 2h
**Depends:** S0-T09

**Redis:** cache.t3.micro, single node
**CloudFront:** origin=S3, cache policies for HLS segments"

gh issue create --title "S12-T04 — Configure GitHub Actions CI/CD pipeline" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 3h
**Depends:** S0-T07, S12-T01

**Pipeline steps:**
lint → pytest → docker build → ECR push → staging auto-deploy → manual approval → prod blue-green deploy"

gh issue create --title "S12-T05 — Configure Secrets Manager and deploy to staging" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 3h
**Depends:** S12-T01, S12-T03

**All .env vars in AWS Secrets Manager, injected at ECS runtime**

**Done When:**
https://api-staging.nearkart.in/api/v1/health/ returns 200 ✅"

gh issue create --title "S12-T06 — UAT with 5 real vendors and 10 customers" \
  --label "Sprint-12,Backend" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 8h
**Depends:** S12-T05

**Vendor UAT:** store setup, add products, post videos, create invoices
**Customer UAT:** discover stores, watch videos, chat, reserve products"

gh issue create --title "S12-T07 — Fix critical UAT bugs" \
  --label "Sprint-12,Backend" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 8h
**Depends:** S12-T06

**Fix all P0 and P1 issues found during UAT before proceeding to production."

gh issue create --title "S12-T08 — Security checklist and performance test" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 5h
**Depends:** S12-T05

**Security checklist:**
- DEBUG=False ✅
- CORS configured ✅
- Rate limits active ✅
- S3 not public ✅
- HTTPS + HSTS ✅

**Performance test:**
Locust: 100 concurrent users, all APIs under 500ms"

gh issue create --title "S12-T09 — Production deployment — GO LIVE 🚀" \
  --label "Sprint-12,DevOps" \
  --body "**Sprint:** 12 — Staging + UAT + Production
**Time:** 2h
**Depends:** S12-T07, S12-T08

**Final step — promote to production!**

**Done When:**
https://api.nearkart.in/api/v1/health/ returns 200 ✅

🎉 NearKart is LIVE!"

echo ""
echo "=============================================="
echo "🎉 ALL 99 NEARKART TASKS CREATED IN GITHUB!"
echo "=============================================="
echo ""
echo "Summary:"
echo "  Sprint 0  — 16 issues ✅"
echo "  Sprint 1  — 14 issues ✅"
echo "  Sprint 2  —  7 issues ✅"
echo "  Sprint 3  —  6 issues ✅"
echo "  Sprint 4  —  6 issues ✅"
echo "  Sprint 5  —  6 issues ✅"
echo "  Sprint 6  —  6 issues ✅"
echo "  Sprint 7  —  4 issues ✅"
echo "  Sprint 8  —  5 issues ✅"
echo "  Sprint 9  — 10 issues ✅"
echo "  Sprint 10 —  5 issues ✅"
echo "  Sprint 11 —  5 issues ✅"
echo "  Sprint 12 —  9 issues ✅"
echo "  TOTAL     — 99 issues ✅"
echo ""
echo "Next steps:"
echo "  1. Go to your GitHub repo → Issues tab"
echo "  2. Create a Project Board (Projects tab)"
echo "  3. Add all issues to the board"
echo "  4. Set columns: Backlog | In Progress | Review | Done"
echo "  5. Start Sprint 0 — S0-T01!"
