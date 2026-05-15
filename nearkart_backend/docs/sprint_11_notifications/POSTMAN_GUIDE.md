# Sprint 11 — Notifications Postman Guide

## Collection Setup

Create a new Postman folder: **"11 — Notifications"**

Set collection variable `base_url = http://localhost:8000/api/v1`

---

## Pre-condition

You need a vendor JWT in `{{vendor_token}}` and customer JWT in `{{customer_token}}`.

---

## Requests

### 1. Register Device Token (Vendor)

```
POST {{base_url}}/notifications/device-token/
Authorization: Bearer {{vendor_token}}
Content-Type: application/json

{
  "fcm_token": "ExponentPushToken[test_token_abc123]",
  "device_type": "android"
}
```

Expected: `200 {"message": "Device token registered."}`

---

### 2. List Notifications

```
GET {{base_url}}/notifications/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 [{"id": "...", "notification_type": "...", "title": "...", "body": "...", "is_read": false, "created_at": "..."}, ...]`

---

### 3. Get Unread Count

```
GET {{base_url}}/notifications/unread-count/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 {"unread_count": 3}`

---

### 4. Mark One Notification Read

```
POST {{base_url}}/notifications/{{notification_id}}/read/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 {"message": "Marked as read."}`

---

### 5. Mark All Read

```
POST {{base_url}}/notifications/read-all/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 {"marked_read": 3}`

---

## How to Trigger Each Notification Type

| Notification | How to trigger |
|-------------|---------------|
| `new_message` | Customer sends WS message to a conversation |
| `reservation_created` | Customer: `POST /reservations/` |
| `reservation_confirmed` | Vendor: `POST /reservations/<id>/confirm/` |
| `reservation_cancelled` | Vendor: `POST /reservations/<id>/cancel/` |
| `reservation_expired` | Celery task or let hold expire |
| `new_follower` | Customer: `POST /stores/<id>/follow/` |
| `new_review` | Customer: `POST /stores/<id>/review/` |
| `store_opened` | Vendor: `PUT /stores/<id>/` with `{"is_open": true}` |
| `video_liked` | Customer: `POST /videos/<id>/like/` |
| `wallet_topup` | Admin/Postman: `POST /billing/wallet/topup/` |
| `group_added` | Admin: `POST /groups/<id>/members/` |
| `group_removed` | Admin: `DELETE /groups/<id>/members/<user_id>/` |
| `group_product_shared` | Member: `POST /groups/<id>/products/` |
| `group_product_finalized` | Admin: `POST /groups/<id>/products/<sp_id>/finalize/` |
| `group_admin_promoted` | Admin: `POST /groups/<id>/members/<user_id>/make-admin/` |

---

## Check Dev FCM Logs

When a push is triggered, check the Django server console for:

```
INFO apps.notifications.fcm FCM-DEV] → +919876543210 | title="New message from Customer" body="..." tokens=1
```

This confirms push would be sent in production.

---

## Postman Test Script (for List Notifications)

Add to "Tests" tab on the List Notifications request:

```javascript
pm.test("Status is 200", () => pm.response.to.have.status(200));
const data = pm.response.json();
pm.test("Returns array", () => pm.expect(Array.isArray(data)).to.be.true);
if (data.length > 0) {
    pm.collectionVariables.set("notification_id", data[0].id);
    pm.test("First notification has required fields", () => {
        pm.expect(data[0]).to.have.all.keys("id", "notification_type", "title", "body", "is_read", "created_at");
    });
}
```
