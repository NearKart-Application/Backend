# Sprint 11 — Notifications

**Status:** Done ✅
**Verified on:** 2026-05-15

---

## What This Sprint Does

Adds a full notification system to NearKart: every important user event (new message, reservation, follow, review, like, wallet top-up, subscription, group actions) sends both an **in-app inbox notification** (stored in the database) and a **Firebase FCM push notification** to the user's device.

---

## Architecture

```
Event happens (e.g. reservation confirmed)
        ↓
NotificationService.notify_*()
        ↓
Notification record saved to DB (in-app inbox)
        +
FCMService.send_push() → Firebase → Device
```

- `apps/notifications/fcm.py` — FCMService (single source of truth for push)
- `apps/notifications/services.py` — NotificationService (18 helper methods)
- `apps/notifications/models.py` — Notification model (inbox)
- `apps/notifications/tasks.py` — Celery tasks for subscription reminders

---

## 18 Notification Types

| Type | Triggered By | Recipient |
|------|-------------|-----------|
| `new_message` | Chat WebSocket message | Other party in conversation |
| `reservation_created` | Customer creates reservation | Vendor |
| `reservation_confirmed` | Vendor confirms | Customer |
| `reservation_cancelled` | Vendor cancels | Customer |
| `reservation_expired` | Celery: hold expired | Customer |
| `new_follower` | User follows store | Vendor |
| `new_review` | User reviews store | Vendor |
| `store_opened` | Vendor sets `is_open=true` | All followers (bulk) |
| `video_liked` | User likes video | Vendor |
| `video_ready` | (Future: transcoding done) | Vendor |
| `wallet_topup` | Admin tops up wallet | Vendor |
| `subscription_expiring` | Celery daily 9 AM | Vendors expiring in 3 days |
| `subscription_expired` | Celery daily 9:05 AM | Vendors whose sub expired |
| `group_added` | Admin adds member to group | Added user |
| `group_removed` | Admin removes member | Removed user |
| `group_product_shared` | Member shares product | All other group members |
| `group_product_finalized` | Admin finalizes product | All group members |
| `group_admin_promoted` | Admin promotes member | Promoted user |

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/notifications/` | JWT | List last 50 notifications (inbox) |
| GET | `/api/v1/notifications/unread-count/` | JWT | Badge count for unread notifications |
| POST | `/api/v1/notifications/<id>/read/` | JWT | Mark one notification as read |
| POST | `/api/v1/notifications/read-all/` | JWT | Mark all notifications as read |
| POST | `/api/v1/notifications/device-token/` | JWT | Register or refresh FCM device token |

---

## Device Token Registration

Clients must register their FCM token after login:

```
POST /api/v1/notifications/device-token/
{
  "fcm_token": "fcm_token_from_firebase_sdk",
  "device_type": "android"   // or "ios" or "web"
}
```

Returns `200 {"message": "Device token registered."}`.

---

## Dev Mode

In dev mode (no Firebase credentials configured), FCM pushes are logged to console instead of sent:

```
[FCM-DEV] → +919876543210 | title="New message from Ravi Fashion" body="Hello!" tokens=1
```

---

## Celery Beat Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `notifications.notify_expiring_subscriptions` | Daily 9:00 AM | Notify vendors whose sub expires in ~3 days |
| `notifications.notify_expired_subscriptions` | Daily 9:05 AM | Notify vendors whose sub expired in last 24h |

---

## Migration

```bash
python manage.py migrate apps.notifications
```

Creates table: `notifications`
Indexes: `notif_recipient_read_idx`, `notif_recipient_time_idx`

---

## Files Changed / Created

| File | Change |
|------|--------|
| `apps/notifications/fcm.py` | New — FCMService (moved from chat, shared project-wide) |
| `apps/notifications/models.py` | New — Notification model, 18 NotificationType choices |
| `apps/notifications/services.py` | New — NotificationService with 18 helper methods + SMSService |
| `apps/notifications/views.py` | New — 5 inbox + device token views |
| `apps/notifications/serializers.py` | New — NotificationSerializer, DeviceTokenRegisterSerializer |
| `apps/notifications/urls.py` | New — 5 URL patterns |
| `apps/notifications/tasks.py` | New — 2 Celery beat tasks |
| `apps/notifications/admin.py` | New — NotificationAdmin |
| `apps/notifications/migrations/0001_initial.py` | New — creates notifications table |
| `apps/chat/consumers.py` | Updated — uses NotificationService instead of direct FCM |
| `apps/chat/services.py` | Updated — imports FCMService from notifications.fcm |
| `apps/reservations/services.py` | Updated — hooks for created/confirmed/cancelled/expired |
| `apps/stores/services.py` | Updated — hooks for new_follower, new_review |
| `apps/stores/views.py` | Updated — store_opened hook on is_open flip |
| `apps/videos/views.py` | Updated — video_liked hook |
| `apps/billing/services.py` | Updated — wallet_topup hook |
| `apps/groups/services.py` | Updated — hooks for add/remove/share/finalize/make_admin |
| `apps/groups/views.py` | Updated — passes added_by to GroupService.add_member |
| `config/settings/base.py` | Updated — Celery beat schedule for 2 tasks |
| `config/urls.py` | Updated — notifications URL include |
