# Word Doc Update — Sprint 29

Add the following section to `NearKart_Master_API_Testing_Guide.docx` after the Sprint 28 section.

---

## Sprint 29 — Backend Performance Hardening · Bug Fixes
**Branch:** sprint-13-localization-video | **Date:** 2026-06-17

No new endpoints. All changes are backward-compatible.

---

### Response Shape Change: Paginated Endpoints

The following endpoints now return a **paginated envelope** instead of a flat list.
Update any client code or Postman tests that iterate the raw array directly.

**New response shape:**
```json
{
  "count": 123,
  "next": "...?limit=20&offset=20",
  "previous": null,
  "results": [ ... ]
}
```

**Affected endpoints:**

| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/api/v1/vendor/products/` | Vendor JWT |
| GET | `/api/v1/videos/my/` | Vendor JWT |
| GET | `/api/v1/analytics/videos/` | Vendor JWT |
| GET | `/api/v1/billing/transactions/` | Vendor JWT |
| GET | `/api/v1/loyalty/transactions/` | Vendor JWT |
| GET | `/api/v1/admin/stores/` | Admin JWT |
| GET | `/api/v1/admin/users/` | Admin JWT |
| GET | `/api/v1/admin/products/` | Admin JWT |

**Pagination query params (all endpoints):**

| Param | Default | Max | Notes |
|-------|---------|-----|-------|
| `limit` | 20 | 100 | Items per page |
| `offset` | 0 | — | Skip N items |

---

### Bug Fixed: Review Reply Endpoint

**POST** `/api/v1/stores/{store_id}/reviews/{review_id}/reply/`

Previously crashed with `500 NameError` due to unbound variable in `except` clause.
Now correctly returns `404` for reviews not belonging to the vendor's store.

---

### Bug Fixed: Monthly Earnings PDF Export

**GET** `/api/v1/stores/{store_id}/earnings/pdf/?month=YYYY-MM`

Previously crashed with `500 AttributeError` (`inv.total_amount` and `inv.invoice_number`
do not exist on Invoice model). Now generates PDF correctly.

Invoice number format in PDF: `#XXXXXXXX` (first 8 chars of UUID, uppercase)

---

### Bug Fixed: Review Notification Title

When a customer posts a store review, the vendor now receives a notification with:
- **Title:** `"New Review — <Store Name>"`
- **data.store_id:** UUID of the store

Previously the notification title contained the customer's phone number instead of the store name.

---

### Performance: No API Changes

All performance fixes are internal (query optimization, bulk DB writes, DB indexes).
No request/response contract changes. No new fields. No behavioral changes for clients.

---

### Deploy Steps for This Sprint

```bash
git pull origin sprint-13-localization-video
python manage.py migrate          # 4 new index migrations
supervisorctl restart celery celerybeat gunicorn
```

---

### Postman Tests to Update

For any saved requests that expect a **flat list** from the endpoints listed above,
update the response parsing to use `response.results` instead of `response` directly.

Example update:
```javascript
// Before (flat list)
const products = pm.response.json();

// After (paginated)
const data = pm.response.json();
const products = data.results;
pm.test("Count present", () => pm.expect(data).to.have.property('count'));
```
