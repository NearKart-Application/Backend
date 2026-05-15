# Sprint 4 — Code Reference

All files, classes, fields, methods, and design decisions for the Video Module.

---

## `apps/videos/models.py`

### class `Video`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | UUIDField | uuid4 | Primary key |
| `store` | FK → Store | — | CASCADE delete; `related_name='videos'` |
| `title` | CharField(200) | — | Required |
| `description` | TextField | `''` | Optional |
| `raw_s3_key` | CharField(500) | `''` | S3 key of original uploaded file, e.g. `videos/raw/{store_id}/{video_id}/original.mp4` |
| `hls_s3_key` | CharField(500) | `''` | S3 key of HLS master manifest, e.g. `videos/hls/{store_id}/{video_id}/master.m3u8` |
| `thumbnail_url` | URLField(500) | `''` | Filled after transcoding |
| `video_url` | URLField(500) | `''` | CDN URL of HLS .m3u8 — filled after transcoding |
| `status` | CharField(20) | `pending_upload` | Enum: `pending_upload` → `processing` → `ready` / `failed` / `expired` |
| `duration_seconds` | PositiveIntegerField | `0` | Set by vendor on confirm-upload |
| `location` | PointField(geography=True) | null | Copied from store.location at save time |
| `locality` | CharField(200) | `''` | Copied from store.locality at save time |
| `view_count` | PositiveIntegerField | `0` | Incremented via `F()` on every detail GET |
| `like_count` | PositiveIntegerField | `0` | Incremented/decremented via `F()` on like toggle |
| `is_visible` | BooleanField | `True` | db_index; set False when expired or deleted softly |
| `expires_at` | DateTimeField | null | Auto-set to `now + VIDEO_EXPIRY_DAYS` on first save |
| `created_at` | DateTimeField | auto | |
| `updated_at` | DateTimeField | auto | |

**Status constants:**
```python
Video.STATUS_PENDING    = 'pending_upload'
Video.STATUS_PROCESSING = 'processing'
Video.STATUS_READY      = 'ready'
Video.STATUS_FAILED     = 'failed'
Video.STATUS_EXPIRED    = 'expired'
```

**`save()` logic:**
- If `expires_at` not set → calculate from `settings.VIDEO_EXPIRY_DAYS` (default 30)
- If `location` is null → try to copy from `self.store.location` + `self.store.locality`

**Indexes:**
- `(status, is_visible)` — feed queries filter on both
- `(store, status)` — vendor dashboard queries

---

### class `VideoLike`

| Field | Type | Notes |
|-------|------|-------|
| `user` | FK → User | CASCADE; `related_name='video_likes'` |
| `video` | FK → Video | CASCADE; `related_name='likes'` |
| `created_at` | DateTimeField | auto |

`unique_together = ['user', 'video']` — prevents duplicate likes.

---

## `apps/videos/serializers.py`

### `VideoSerializer`
Read serializer for all video responses.

| Field | Source | Notes |
|-------|--------|-------|
| `store_name` | `store.name` | read_only |
| `store_id` | `store.id` | read_only |
| `distance_km` | SerializerMethodField | from `Distance` annotation on queryset |
| `is_liked` | SerializerMethodField | checks `obj.likes.filter(user=request.user)` if authenticated |

**`get_distance_km(obj)`** — returns `obj.distance.km` rounded to 2dp if annotated, else `null`.
**`get_is_liked(obj)`** — returns `True` if request.user has a `VideoLike` for this video.

### `VideoUploadRequestSerializer`
Write serializer for `POST /videos/request-upload/`.

| Field | Required | Notes |
|-------|----------|-------|
| `title` | Yes | max_length=200 |
| `description` | No | allow_blank, default `''` |

---

## `apps/videos/services.py`

### `AWSService`

**`_is_dev_aws() → bool`**
Detects fake/example AWS credentials by checking if `AWS_ACCESS_KEY_ID` contains `'EXAMPLE'`. Used to skip real S3 calls in dev.

**`AWSService.generate_presigned_upload_url(s3_key, content_type='video/mp4') → str`**
- Dev mode → returns `https://mock-s3.dev/{s3_key}?dev=true`
- Production → calls `boto3.client('s3').generate_presigned_url('put_object', ...)` with `ExpiresIn=AWS_PRESIGNED_URL_EXPIRY` (default 900s)
- Returns `''` on `ClientError`

**`AWSService.cdn_url(s3_key) → str`**
Builds `https://{AWS_CDN_DOMAIN}/{s3_key}`. Falls back to `{bucket}.s3.{region}.amazonaws.com` if `CDN_DOMAIN` not set.

---

### `VideoService`

**`request_upload(store, title, description='') → (Video, upload_url)`**
- Generates a `uuid4` for the video
- Builds S3 key: `videos/raw/{store.id}/{video_id}/original.mp4`
- Calls `AWSService.generate_presigned_upload_url`
- Creates `Video` record with `status=pending_upload`
- Returns `(video, upload_url)`

**`confirm_upload(video, duration_seconds=0) → Video`**
- Sets `video.status = 'processing'`, `video.duration_seconds`
- Calls `transcode_video.delay(str(video.id))` — Celery async task
- Saves with `update_fields` (efficient — only updates changed columns)

**`get_feed(lat, lng, radius_km=5, store_id=None) → QuerySet`**
- Builds `Point(lng, lat, srid=4326)` — note: PostGIS is (x=lng, y=lat)
- Filters: `status=ready`, `is_visible=True`, `expires_at > now`
- `location__dwithin=(point, D(km=radius_km))` — PostGIS geography DWithin in km
- Annotates with `Distance('location', point)` for `distance_km` in serializer
- Orders by `distance`, then `-created_at`
- Optional `store_id` filter
- Sliced to max 50 results

**`increment_view(video) → None`**
Uses `Video.objects.filter(id=video.id).update(view_count=F('view_count') + 1)`. Single SQL UPDATE — no read-modify-write race.

**`toggle_like(user, video) → bool`**
- `VideoLike.objects.get_or_create(user=user, video=video)`
- If created → `UPDATE SET like_count = like_count + 1` → returns `True`
- If existing → delete like → `UPDATE SET like_count = like_count - 1` → returns `False`
- Both increments use `F()` expressions — safe under concurrent requests

**`expire_old_videos() → int`**
- Bulk UPDATE: `expires_at < now AND status IN (ready, processing)` → `status=expired, is_visible=False`
- Returns count of expired videos (for task logging)

---

## `apps/videos/tasks.py`

### `transcode_video(video_id: str)`
Celery shared task. `bind=True, max_retries=3, default_retry_delay=60`.

**Dev mode path** (`_is_dev_aws()` returns True):
- Sets `status=ready`, `video_url=mock-url`, `thumbnail_url=mock-url`
- Returns immediately — no FFmpeg, no S3

**Production path:**
1. Download raw file from S3 to `/tmp/{video_id}_input.mp4`
2. Run FFmpeg: H.264/AAC → HLS segments in `/tmp/{video_id}_hls/`
   - `hls_time=6` (6-second segments), `crf=23`, `preset=fast`
3. Generate thumbnail at 1s, scale to 480×270
4. Upload all `.m3u8` + `.ts` files to `videos/hls/{store_id}/{video_id}/`
5. Upload thumbnail to `videos/thumbnails/{store_id}/{video_id}/thumb.jpg`
6. Update video: `hls_s3_key`, `video_url`, `thumbnail_url`, `status=ready`
7. Cleanup: remove all local temp files

On exception: sets `status=failed`, calls `self.retry(exc=exc)` — up to 3 retries with 60s delay.

### `delete_expired_videos()`
Celery Beat daily task. Calls `VideoService.expire_old_videos()`, logs count.

---

## `apps/videos/views.py`

### `VideoUploadRequestView` — `POST /videos/request-upload/`
- `permission_classes = [IsAuthenticated, IsVendor]`
- Checks `hasattr(request.user, 'store')` — 400 if vendor has no store
- Validates `VideoUploadRequestSerializer`
- Returns: `video_id`, `upload_url`, `expires_in_seconds`, `message`

### `VideoConfirmUploadView` — `POST /videos/<video_id>/confirm-upload/`
- `permission_classes = [IsAuthenticated, IsVendor]`
- Gets video filtered by `id=video_id AND store=request.user.store` — vendor can only confirm their own video
- 400 if `video.status != 'pending_upload'` — prevents double-confirming
- Passes `duration_seconds` (default 0) to `VideoService.confirm_upload`

### `VideoFeedView` — `GET /videos/feed/`
- `permission_classes = [AllowAny]`
- Requires `lat`, `lng` query params — 400 if missing/invalid
- Optional: `radius` (default 5km), `store_id` (UUID filter)

### `VideoDetailView` — `GET /videos/<video_id>/`
- `permission_classes = [AllowAny]`
- Filters: `status=ready AND is_visible=True` — anything else returns 404
- Calls `VideoService.increment_view(video)` before serializing

### `VideoDeleteView` — `DELETE /videos/<video_id>/delete/`
- `permission_classes = [IsAuthenticated, IsVendor]`
- Filters by `store=request.user.store` — vendor can only delete their own videos
- Hard delete (permanent)

### `VideoLikeView` — `POST /videos/<video_id>/like/`
- `permission_classes = [IsAuthenticated]`
- `request=None` in `@extend_schema` (no body)
- Only works on `status=ready AND is_visible=True` videos

---

## How to Change Things in Future

### Change video expiry duration
`.env` → `VIDEO_EXPIRY_DAYS=60`  (currently 30)

### Change max video duration
`.env` → `VIDEO_MAX_DURATION_SECONDS=90`  (currently 60)
Add server-side validation in `VideoConfirmUploadView` if enforcement is needed.

### Change FFmpeg encoding quality
`tasks.py` → `transcode_video` → change `-crf 23` (lower = better quality, larger file) or `-preset fast` to `medium`.

### Add video thumbnail from client instead of FFmpeg
`VideoConfirmUploadView` — accept a `thumbnail_url` field and skip the FFmpeg thumbnail step in `transcode_video`.

### Add video search (by title)
Add `pg_trgm` GIN index on `Video.title` (same pattern as Product search in Sprint 3). Add `GET /videos/search/?q=` endpoint.

### Add store video count to StoreSerializer
`StoreSerializer` — add `SerializerMethodField`: `return obj.videos.filter(status='ready').count()`.
