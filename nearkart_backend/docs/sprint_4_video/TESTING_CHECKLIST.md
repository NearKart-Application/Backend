# Sprint 4 — Testing Checklist

**Verified on:** 2026-05-15
**Environment:** Docker local, dev mode (mock AWS)

---

## Upload Flow
- [x] POST /videos/request-upload/ with vendor token → 201, returns `video_id` and `upload_url`
- [x] `upload_url` is mock S3 URL in dev mode (`https://mock-s3.dev/...`)
- [x] `expires_in_seconds` = 900 returned
- [x] Video record created in DB with `status=pending_upload`
- [x] POST /videos/request-upload/ with no store → 400 "Create a store first"
- [x] POST /videos/request-upload/ with missing `title` → 400 validation_error
- [x] POST /videos/request-upload/ with customer token → 403 Vendor access only

## Confirm Upload / Transcoding
- [x] POST /videos/<id>/confirm-upload/ → 200, `status=processing`
- [x] Celery task runs in dev mode → video marked `status=ready` within ~2 seconds
- [x] `video_url` and `thumbnail_url` populated with mock URLs in dev
- [x] POST /videos/<id>/confirm-upload/ on already-ready video → 400 "already in ready state"
- [x] POST /videos/<id>/confirm-upload/ on another vendor's video → 404

## Video Feed
- [x] GET /videos/feed/?lat=13.0418&lng=80.2341&radius=10 → 200, array with video
- [x] GET /videos/feed/ without lat/lng → 400 "lat and lng are required numbers"
- [x] Feed only returns `status=ready AND is_visible=True` videos
- [x] GET /videos/feed/?store_id=<uuid> → filtered to that store

## Video Detail
- [x] GET /videos/<id>/ → 200, full video object
- [x] view_count increments by 1 on each GET
- [x] GET /videos/<id>/ on processing video → 404
- [x] GET /videos/00000000-0000-0000-0000-000000000000/ → 404

## Like / Unlike
- [x] POST /videos/<id>/like/ (1st call) → `{"liked": true, "message": "Liked."}`
- [x] POST /videos/<id>/like/ (2nd call) → `{"liked": false, "message": "Unliked."}`
- [x] like_count increments and decrements correctly in DB
- [x] POST /videos/<id>/like/ without token → 401

## Delete
- [x] DELETE /videos/<id>/delete/ with vendor token → 204 No Content
- [x] GET /videos/<id>/ after delete → 404
- [x] DELETE with customer token → 403 Vendor access only
- [x] DELETE another vendor's video → 404 not found (filtered by own store)

## Admin
- [x] Video and VideoLike visible in Django Admin at http://localhost:8000/admin/
- [x] `is_visible` editable inline in video list
