# Sprint 16 — Postman Guide

Base URL: `http://localhost:8000/api/v1/`

## 1. Submit a Review (customer)

**Requirement:** customer must have a completed reservation at the store.

```
POST /stores/{store_id}/reviews/
Authorization: Bearer <customer_token>
Content-Type: application/json

{
  "rating": 5,
  "comment": "Excellent service, products were exactly as described!"
}
```

**Success 200:**
```json
{
  "id": "uuid",
  "user_phone": "+91900000000X",
  "rating": 5,
  "comment": "Excellent service...",
  "vendor_reply": "",
  "vendor_reply_at": null,
  "created_at": "2026-05-23T10:00:00Z"
}
```

**403 (no completed reservation):**
```json
{
  "error": "no_completed_reservation",
  "message": "You can only review a store after completing a reservation there."
}
```

---

## 2. List Store Reviews (public)

```
GET /stores/{store_id}/reviews/
```

**Success 200:**
```json
{
  "results": [
    {
      "id": "uuid",
      "user_name": "Arj****",
      "rating": 5,
      "comment": "Excellent service...",
      "vendor_reply": "Thank you for your kind words!",
      "vendor_reply_at": "2026-05-23T11:00:00Z",
      "created_at": "2026-05-23T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

## 3. Vendor Reply to Review

```
POST /stores/{store_id}/reviews/{review_id}/reply/
Authorization: Bearer <vendor_token>
Content-Type: application/json

{
  "reply": "Thank you! We look forward to seeing you again soon."
}
```

**Success 200:** Returns updated review object with `vendor_reply` populated.

---

## 4. Vendor — List All Reviews for My Store

```
GET /stores/{store_id}/reviews/vendor/
Authorization: Bearer <vendor_token>
```

**Success 200:**
```json
{
  "results": [...],
  "count": 3
}
```

---

## 5. Customer — Get My Reviews

```
GET /stores/mine/reviews/
Authorization: Bearer <customer_token>
```

**Success 200:**
```json
{
  "results": [
    {
      "id": "uuid",
      "rating": 5,
      "comment": "Great store!",
      "vendor_reply": "",
      "vendor_reply_at": null,
      "store_id": "uuid",
      "store_name": "Sneha's Fashion House",
      "created_at": "2026-05-23T10:00:00Z"
    }
  ],
  "count": 1
}
```
