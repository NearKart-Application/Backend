# Sprint 21 — Postman Guide

## Setup

1. Set `{{base_url}}` = `http://localhost:8000/api/v1`
2. Set `{{admin_token}}` = JWT for an admin-role user
3. Set `{{vendor_token}}` = JWT for a vendor-role user
4. All admin requests: `Authorization: Bearer {{admin_token}}`
5. All vendor requests: `Authorization: Bearer {{vendor_token}}`

---

## Category Management

### 1. Create Category

```
POST {{base_url}}/admin-panel/categories/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "name": "Groceries",
    "slug": "groceries",
    "icon": "🛒",
    "display_order": 1,
    "is_active": true
}
```

Expected: `201 Created`
```json
{
    "id": "uuid",
    "name": "Groceries",
    "slug": "groceries",
    "icon": "🛒",
    "display_order": 1,
    "is_active": true,
    "created_at": "...",
    "updated_at": "..."
}
```
> Save the returned `id` as `{{category_id}}`

---

### 2. List All Categories (Admin)

```
GET {{base_url}}/admin-panel/categories/
Authorization: Bearer {{admin_token}}
```

Expected: `200 OK` — list includes both active and inactive categories.

---

### 3. Update Category

```
PATCH {{base_url}}/admin-panel/categories/{{category_id}}/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "icon": "🥦",
    "display_order": 2
}
```

Expected: `200 OK` with updated fields.

---

### 4. Hide a Category

```
PATCH {{base_url}}/admin-panel/categories/{{category_id}}/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "is_active": false
}
```

Expected: `200 OK` — category now excluded from the public endpoint.

---

### 5. Delete Category

```
DELETE {{base_url}}/admin-panel/categories/{{category_id}}/
Authorization: Bearer {{admin_token}}
```

Expected: `204 No Content`

---

### 6. Public Category List (Vendor / Customer)

```
GET {{base_url}}/products/categories/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 OK` — only `is_active: true` categories returned.

---

## Offer Template Management

### 7. Create Offer Template

```
POST {{base_url}}/admin-panel/offer-templates/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "name": "Summer Sale",
    "description_template": "Enjoy our special summer discounts on selected items!",
    "default_discount_pct": 20,
    "badge_text": "HOT",
    "emoji": "☀️",
    "image_url": "",
    "is_active": true,
    "is_default": true,
    "display_order": 1
}
```

Expected: `201 Created`
```json
{
    "id": "uuid",
    "name": "Summer Sale",
    "default_discount_pct": 20,
    "badge_text": "HOT",
    "emoji": "☀️",
    "is_active": true,
    "is_default": true,
    "display_order": 1,
    ...
}
```
> Save the returned `id` as `{{template_id}}`

---

### 8. Create Second Template (Tests Single-Default Invariant)

```
POST {{base_url}}/admin-panel/offer-templates/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "name": "Weekend Deal",
    "description_template": "Weekend specials — grab them before Monday!",
    "default_discount_pct": 15,
    "badge_text": "DEAL",
    "emoji": "🎉",
    "is_active": true,
    "is_default": true,
    "display_order": 2
}
```

Expected: `201 Created`
Then verify: `GET {{base_url}}/admin-panel/offer-templates/` — only "Weekend Deal" should have `is_default: true`. "Summer Sale" should now have `is_default: false`.

---

### 9. List All Offer Templates (Admin)

```
GET {{base_url}}/admin-panel/offer-templates/
Authorization: Bearer {{admin_token}}
```

Expected: `200 OK` — all templates including inactive.

---

### 10. Update Offer Template

```
PATCH {{base_url}}/admin-panel/offer-templates/{{template_id}}/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "badge_text": "SALE",
    "default_discount_pct": 25
}
```

Expected: `200 OK`

---

### 11. Set as Default

```
PATCH {{base_url}}/admin-panel/offer-templates/{{template_id}}/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "is_default": true
}
```

Expected: `200 OK` — this template becomes default, previous default is cleared.

---

### 12. Hide an Offer Template

```
PATCH {{base_url}}/admin-panel/offer-templates/{{template_id}}/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "is_active": false
}
```

Expected: `200 OK` — template excluded from vendor public endpoint.

---

### 13. Delete Offer Template

```
DELETE {{base_url}}/admin-panel/offer-templates/{{template_id}}/
Authorization: Bearer {{admin_token}}
```

Expected: `204 No Content`

---

### 14. Public Offer Templates (Vendor)

```
GET {{base_url}}/stores/offer-templates/
Authorization: Bearer {{vendor_token}}
```

Expected: `200 OK` — only active templates returned; ordered by `display_order`.

---

## Error Cases

### Wrong role on admin endpoint
```
GET {{base_url}}/admin-panel/categories/
Authorization: Bearer {{vendor_token}}
```
Expected: `403 Forbidden`

### Duplicate slug
```
POST {{base_url}}/admin-panel/categories/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{
    "name": "Groceries Again",
    "slug": "groceries",
    "icon": "🛒",
    "display_order": 5,
    "is_active": true
}
```
Expected: `400 Bad Request` — slug already taken.

### Non-existent ID
```
PATCH {{base_url}}/admin-panel/categories/00000000-0000-0000-0000-000000000000/
Authorization: Bearer {{admin_token}}
Content-Type: application/json

{ "name": "Ghost" }
```
Expected: `404 Not Found`
