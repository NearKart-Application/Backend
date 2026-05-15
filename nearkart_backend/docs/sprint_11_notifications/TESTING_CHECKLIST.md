# Sprint 11 — Notifications Testing Checklist

**Branch:** `sprint-11-notifications`

---

## Pre-requisites

- [ ] Run `python manage.py migrate` — creates `notifications` table
- [ ] Vendor token, Customer token, and a Store in DB
- [ ] Optionally: register FCM token for a device to test push

---

## Device Token Registration

- [ ] `POST /api/v1/notifications/device-token/` with vendor JWT
  - Body: `{"fcm_token": "test_token_abc123", "device_type": "android"}`
  - Expected: `200 {"message": "Device token registered."}`
- [ ] Re-register same token — should update, not duplicate
- [ ] Check Django Admin → Device Tokens → token appears with `is_active=true`

---

## In-App Inbox

- [ ] `GET /api/v1/notifications/` with fresh user (no notifications)
  - Expected: `200 []`
- [ ] After triggering any event below, inbox shows the notification
- [ ] `GET /api/v1/notifications/unread-count/` — returns `{"unread_count": N}`
- [ ] `POST /api/v1/notifications/<id>/read/` — marks one notification read
  - Expected: `200 {"message": "Marked as read."}`
  - Re-call — still `200` (idempotent)
- [ ] `POST /api/v1/notifications/read-all/` — marks all read
  - Expected: `200 {"marked_read": N}`
  - `GET /api/v1/notifications/unread-count/` → `{"unread_count": 0}`

---

## Chat — new_message

- [ ] Connect customer WebSocket to a conversation → send a message
  - Vendor inbox: notification of type `new_message` appears
  - Dev log shows: `[FCM-DEV] → vendor_phone | title="New message from Customer"`
- [ ] Vendor sends a message
  - Customer inbox: `new_message` notification appears

---

## Reservations

- [ ] `POST /api/v1/reservations/` (as customer)
  - Vendor inbox: `reservation_created` notification
- [ ] `POST /api/v1/reservations/<id>/confirm/` (as vendor)
  - Customer inbox: `reservation_confirmed` notification
- [ ] `POST /api/v1/reservations/<id>/cancel/` (as vendor)
  - Customer inbox: `reservation_cancelled` notification

---

## Stores

- [ ] `POST /api/v1/stores/<id>/follow/` (as customer, new follow)
  - Vendor inbox: `new_follower` notification
- [ ] Unfollow then re-follow — each new follow triggers notification
- [ ] `POST /api/v1/stores/<id>/review/` (as customer)
  - Vendor inbox: `new_review` notification
- [ ] `PUT /api/v1/stores/<id>/` — set `is_open: true` (store was closed)
  - All followers' inboxes: `store_opened` notification (bulk)
  - Set `is_open: true` again — no duplicate notification (already open)

---

## Videos

- [ ] `POST /api/v1/videos/<id>/like/` (as customer)
  - Vendor inbox: `video_liked` notification
- [ ] Unlike then like again — notification each time

---

## Billing

- [ ] `POST /api/v1/billing/wallet/topup/` (admin/Postman)
  - Vendor inbox: `wallet_topup` notification

---

## Groups

- [ ] Create group, add a member
  - Added user's inbox: `group_added` notification (with adder's name)
- [ ] Remove a member
  - Removed user's inbox: `group_removed` notification
- [ ] Share a product in group
  - All other members' inboxes: `group_product_shared` notification
- [ ] Admin finalizes a shared product
  - All members' inboxes: `group_product_finalized` notification
- [ ] Admin promotes a member to admin
  - Promoted user's inbox: `group_admin_promoted` notification

---

## Celery Tasks (manual trigger)

```bash
# In Docker or shell with Django env:
python manage.py shell -c "from apps.notifications.tasks import notify_expiring_subscriptions; notify_expiring_subscriptions()"
python manage.py shell -c "from apps.notifications.tasks import notify_expired_subscriptions; notify_expired_subscriptions()"
```

- [ ] `notify_expiring_subscriptions` — creates notifications for vendors whose sub expires in ~3 days
- [ ] `notify_expired_subscriptions` — creates notifications for vendors whose sub expired in last 24h

---

## Django Admin Checks

- [ ] Admin → Notifications → can see all notification records
- [ ] Filter by `notification_type`, `is_read`
- [ ] Search by phone number, title

---

## Error Cases

| Scenario | Expected |
|----------|---------|
| `POST /device-token/` without `fcm_token` | `400` validation error |
| `POST /device-token/` with invalid device_type | `400` validation error |
| `POST /notifications/<bad-uuid>/read/` | `404` not found |
| `GET /notifications/` without JWT | `401` unauthorized |
| `POST /notifications/read-all/` — no unread | `200 {"marked_read": 0}` |
