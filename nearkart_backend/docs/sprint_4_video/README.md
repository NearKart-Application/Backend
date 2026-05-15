# Sprint 4 — Video Module

**Goal:** Vendor uploads a product video. Celery + FFmpeg transcodes to HLS. Location-based video feed for customers.
**Status:** Done ✅
**Completed:** 2026-05-15
**Depends on:** Sprint 3 (Store + Product)

---

## What Was Built

### Models
| Model | Purpose |
|-------|---------|
| `Video` | Vendor-uploaded product video — stores S3 keys, HLS URL, thumbnail, status, location, view/like counts |
| `VideoLike` | User ↔ Video toggle like (unique_together) |

### Endpoints (8)
| Method | URL | Auth | What it does |
|--------|-----|------|-------------|
| POST | `/api/v1/videos/request-upload/` | Vendor JWT | Returns presigned S3 PUT URL + `video_id` |
| POST | `/api/v1/videos/<id>/confirm-upload/` | Vendor JWT | Triggers Celery transcoding; validates `duration_seconds ≤ 60` |
| GET | `/api/v1/videos/my-videos/` | Vendor JWT | List all vendor's videos — all statuses; optional `?status=` filter |
| GET | `/api/v1/videos/feed/` | Public | Location-based video feed (PostGIS DWithin) |
| GET | `/api/v1/videos/<id>/` | Public / Vendor | Detail + view count; vendor sees own video at any status |
| PATCH | `/api/v1/videos/<id>/update/` | Vendor JWT | Update title / description / is_visible |
| DELETE | `/api/v1/videos/<id>/delete/` | Vendor JWT | Permanently delete (own store only) |
| POST | `/api/v1/videos/<id>/like/` | Bearer JWT | Like / unlike toggle |

### Key Technical Decisions
- **Two-step upload**: Presigned S3 URL → vendor uploads directly to S3 → confirm triggers Celery. Django never handles the binary.
- **HLS transcoding**: FFmpeg converts raw MP4 to HLS (.m3u8 + .ts segments). `transcode_video` Celery task with 3 retries.
- **Dev mode**: Fake AWS creds detected → mock upload URLs returned, FFmpeg skipped, video marked `ready` instantly.
- **Location on video**: Copied from store at create time so feed geo-queries use a spatial index on `Video.location`.
- **Expiry**: `expires_at` set to 30 days from upload. Daily Celery Beat task (`delete_expired_videos`) sweeps expired videos.
- **Like count**: Uses `F()` expressions for atomic increment/decrement — no race conditions under concurrent load.
- **Duration validation**: `confirm-upload` rejects `duration_seconds > VIDEO_MAX_DURATION_SECONDS` (60s) — returns 400.
- **Vendor status visibility**: `GET /videos/<id>/` returns the video to its store owner at any status; public only sees `ready + is_visible`.
- **My videos list**: `GET /videos/my-videos/` gives vendor full view of their library including processing/failed videos.

---

## Files Changed
```
apps/videos/models.py                  — Video, VideoLike models
apps/videos/serializers.py             — VideoSerializer, VideoUploadRequestSerializer
apps/videos/services.py                — AWSService, VideoService
apps/videos/tasks.py                   — transcode_video, delete_expired_videos
apps/videos/views.py                   — 8 view classes with @extend_schema
apps/videos/urls.py                    — URL patterns
apps/videos/admin.py                   — Django admin registration
apps/videos/migrations/0001_initial.py — DB migration
```

---

## Docs
- [API_TEST_FLOW.md](API_TEST_FLOW.md) — step-by-step curl/Postman test guide
- [CODE_REFERENCE.md](CODE_REFERENCE.md) — every class, field, method explained
- [POSTMAN_GUIDE.md](POSTMAN_GUIDE.md) — Postman collection and auto-save scripts
- [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) — verification checklist (marked done)
