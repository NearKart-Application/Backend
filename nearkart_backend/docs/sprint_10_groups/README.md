# Sprint 10 — Groups

**Status:** Done ✅
**Verified on:** 2026-05-15

---

## What This Sprint Does

Users can create groups to share products with friends and make collective purchase decisions — like a WhatsApp group but for shopping. Phone numbers are never exposed — users are identified by a private **Profile ID** (e.g. `NK-A3X9K2`).

Two group types:
- **Customer Group** — any user creates, adds friends by Profile ID, shares products, admin finalizes
- **Vendor Group** — vendor creates, can only add customers who follow that store (VIP/exclusive group)

---

## Profile ID

- Every user gets a unique `profile_id` on signup (format: `NK-XXXXXXXX`)
- Shown in the user's own profile (`GET /auth/me/`)
- User shares it with friends outside the app (e.g. via WhatsApp)
- Others search by it: `GET /auth/users/search/?profile_id=NK-A3X9K2` → returns name only (no phone)

---

## Group Flow

```
Create group → Add members → Share products → Finalize → Done
                                           ↘ Delete group (creator)
```

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/api/v1/auth/users/search/` | Any JWT | Search user by Profile ID |
| POST | `/api/v1/groups/` | Any JWT | Create a group |
| GET | `/api/v1/groups/` | Any JWT | List my groups |
| GET | `/api/v1/groups/<id>/` | Member JWT | Group detail with members |
| DELETE | `/api/v1/groups/<id>/` | Creator JWT | Delete group |
| POST | `/api/v1/groups/<id>/members/add/` | Admin JWT | Add member (by profile_id or user_id) |
| DELETE | `/api/v1/groups/<id>/members/<uid>/remove/` | Admin JWT | Remove member |
| POST | `/api/v1/groups/<id>/members/<uid>/make-admin/` | Admin JWT | Promote member to admin |
| POST | `/api/v1/groups/<id>/members/<uid>/remove-admin/` | Admin JWT | Demote admin to member |
| POST | `/api/v1/groups/<id>/leave/` | Member JWT | Leave group |
| GET | `/api/v1/groups/<id>/eligible-members/` | Admin JWT | Vendor: followers not yet in group |
| GET | `/api/v1/groups/<id>/products/` | Member JWT | List shared products |
| POST | `/api/v1/groups/<id>/products/` | Member JWT | Share a product |
| POST | `/api/v1/groups/<id>/products/<sp_id>/finalize/` | Admin JWT | Finalize a product |

---

## Business Rules

| Rule | Detail |
|------|--------|
| No phone numbers | All responses use `profile_id` + `full_name` only |
| Creator is admin | Auto-assigned on group creation |
| Multiple admins | Any admin can promote/demote others (not the creator) |
| Creator is protected | Cannot be removed or demoted; cannot leave (must delete) |
| Customer group — add by Profile ID | `{ "profile_id": "NK-A3X9K2" }` |
| Vendor group — add by User ID | `{ "user_id": "..." }` from eligible-members list |
| Vendor groups — follower check | User must follow the store to be added |
| Any member can share products | Product must be active + visible |
| Only admin can finalize | Marks a shared product as the group's final choice |
| App-only links in notes | External URLs blocked — only `nearkart://` links allowed |

---

## Link Validation

Any `note` field when sharing a product is validated:
- `http://youtube.com/...` → **400 — External links are not allowed**
- `https://instagram.com/...` → **400 — External links are not allowed**
- `nearkart://product/123` → **allowed**
- Plain text with no URLs → **allowed**

---

## Files Changed

| File | Change |
|------|--------|
| `apps/auth_app/models.py` | Added `profile_id` field + auto-generation on signup |
| `apps/auth_app/serializers.py` | `UserSerializer` exposes `profile_id`; `UserSearchSerializer` added |
| `apps/auth_app/views.py` | `UserSearchView` — GET /auth/users/search/ |
| `apps/auth_app/urls.py` | Added `/auth/users/search/` route |
| `apps/auth_app/migrations/0002_user_profile_id.py` | Adds + populates `profile_id` for all users |
| `apps/groups/models.py` | Group, GroupMember, GroupSharedProduct models |
| `apps/groups/services.py` | GroupService — create, add/remove member, make/remove admin, share, finalize |
| `apps/groups/serializers.py` | All serializers use profile_id; link validation on notes |
| `apps/groups/views.py` | 11 views |
| `apps/groups/urls.py` | 10 URL patterns |
| `apps/groups/admin.py` | Group + SharedProduct admin |
| `apps/groups/migrations/0001_initial.py` | Creates groups, group_members, group_shared_products tables |
| `core/validators.py` | `validate_no_external_links()` — reusable for future chat |
