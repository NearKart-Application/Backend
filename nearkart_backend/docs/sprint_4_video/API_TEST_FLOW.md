# Sprint 4 — Video Module API Test Flow

**Base URL:** `http://localhost:8000/api/v1`
**Dev OTP:** always `123456`
**Dev S3:** mock URLs returned — no real AWS upload needed

---

## Prerequisites
1. Docker running: `docker compose up -d`
2. Have a vendor token (phone `+919999999999`) and a store already created (Sprint 3)
3. Have a customer token (phone `+916000000001`)

---

## Full Test Sequence

### STEP 1 — Get Vendor Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919999999999"}'

curl -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+919999999999", "otp": "123456"}'
```
Save the `access` token as `VENDOR_TOKEN`.

---

### STEP 2 — Request Upload URL
```bash
curl -X POST http://localhost:8000/api/v1/videos/request-upload/ \
  -H "Authorization: Bearer $VENDOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summer Kurta Collection",
    "description": "Handwoven cotton kurtas for the season"
  }'
```
**Expected 201:**
```json
{
  "video_id": "82d5ede8-d051-4ad9-9054-c922a87a3773",
  "upload_url": "https://mock-s3.dev/videos/raw/.../original.mp4?dev=true",
  "expires_in_seconds": 900,
  "message": "Upload URL ready. PUT your video file to upload_url..."
}
```
Save `video_id` as `VIDEO_ID`.

> **In production:** PUT the actual video file to `upload_url` using `Content-Type: video/mp4`.
> **In dev:** Skip the PUT — just call confirm-upload directly.

---

### STEP 3 — Confirm Upload (triggers transcoding)
```bash
curl -X POST http://localhost:8000/api/v1/videos/$VIDEO_ID/confirm-upload/ \
  -H "Authorization: Bearer $VENDOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration_seconds": 45}'
```
**Expected 200:**
```json
{
  "video_id": "82d5ede8-...",
  "status": "processing",
  "message": "Transcoding queued. Check GET /videos/<id>/ for status updates."
}
```
> **Dev mode:** Celery task immediately marks the video `ready` with mock URLs.
> Wait 2–3 seconds, then call video detail to verify.

---

### STEP 4 — Video Detail (check status = ready)
```bash
curl http://localhost:8000/api/v1/videos/$VIDEO_ID/
```
**Expected 200:**
```json
{
  "id": "82d5ede8-...",
  "store_id": "6c8adfdd-...",
  "store_name": "Fashion Hub",
  "title": "Summer Kurta Collection",
  "description": "Handwoven cotton kurtas for the season",
  "video_url": "https://mock-s3.dev/videos/hls/.../master.m3u8?dev=true",
  "thumbnail_url": "https://mock-s3.dev/videos/thumbnails/.../thumb.jpg?dev=true",
  "status": "ready",
  "duration_seconds": 45,
  "view_count": 1,
  "like_count": 0,
  "is_liked": false,
  "locality": "Anna Salai",
  "distance_km": null,
  "is_visible": true,
  "expires_at": "2026-06-14T...",
  "created_at": "2026-05-15T...",
  "updated_at": "2026-05-15T..."
}
```
> Note: `view_count` increments by 1 on every GET detail call.

---

### STEP 5 — Video Feed (location-based)
```bash
curl "http://localhost:8000/api/v1/videos/feed/?lat=13.0418&lng=80.2341&radius=10"
```
**Expected 200:** Array of ready videos sorted by distance.
```json
[
  {
    "id": "82d5ede8-...",
    "title": "Summer Kurta Collection",
    "status": "ready",
    "video_url": "https://mock-s3.dev/...",
    "distance_km": 0.45
  }
]
```

Filter by store:
```bash
curl "http://localhost:8000/api/v1/videos/feed/?lat=13.0418&lng=80.2341&store_id=6c8adfdd-..."
```

---

### STEP 6 — Like / Unlike Toggle
```bash
# Get customer token first
curl -X POST http://localhost:8000/api/v1/auth/otp/send/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+916000000001"}'

CUSTOMER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/otp/verify/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+916000000001", "otp": "123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# First call — like
curl -X POST http://localhost:8000/api/v1/videos/$VIDEO_ID/like/ \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
# → {"liked": true, "message": "Liked."}

# Second call — unlike
curl -X POST http://localhost:8000/api/v1/videos/$VIDEO_ID/like/ \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
# → {"liked": false, "message": "Unliked."}
```

---

### STEP 7 — Delete Video (vendor owner only)
```bash
curl -X DELETE http://localhost:8000/api/v1/videos/$VIDEO_ID/delete/ \
  -H "Authorization: Bearer $VENDOR_TOKEN"
```
**Expected 204 No Content** (empty body).

Verify it's gone:
```bash
curl http://localhost:8000/api/v1/videos/$VIDEO_ID/
# → 404 {"error": "not_found", "message": "Video not found."}
```

---

## Error Reference

| Scenario | Request | Expected |
|----------|---------|----------|
| No store — request upload | POST /videos/request-upload/ before creating store | 400 — Create a store first |
| Missing title | POST /videos/request-upload/ with no title | 400 — This field is required |
| Customer calls request-upload | Use customer token | 403 — Vendor access only |
| Confirm already-ready video | POST /confirm-upload/ on ready video | 400 — Video is already in "ready" state |
| Feed without lat/lng | GET /videos/feed/ (no params) | 400 — lat and lng are required numbers |
| Detail on processing video | GET /videos/<id>/ while status=processing | 404 — not found (only ready+visible returned) |
| Delete another vendor's video | Use different vendor token | 404 — not found (filtered to own store) |
| Like without auth | POST /videos/<id>/like/ no header | 401 — authentication_failed |
