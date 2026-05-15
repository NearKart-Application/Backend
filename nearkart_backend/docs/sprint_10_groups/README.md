# Sprint 10 — Groups

**Status:** Done ✅
**Verified on:** 2026-05-15

---

## What This Sprint Does

Users can create groups to share products with friends and make collective purchase decisions — like a WhatsApp group but for shopping.

Two group types:
- **Customer Group** — any user creates a group, adds friends by phone number, shares products from any store, admin finalizes the chosen product
- **Vendor Group** — vendor creates a group from their store, can only add customers who follow that store (exclusive VIP group)

---

## Group States

```
created → members added → products shared → product finalized
                       ↘ group deleted (by creator)
```

---

## Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/api/v1/groups/` | Any JWT | Create a group |
| GET | `/api/v1/groups/` | Any JWT | List my groups |
| GET | `/api/v1/groups/<id>/` | Member JWT | Group detail with members |
| DELETE | `/api/v1/groups/<id>/` | Creator JWT | Delete group |
| POST | `/api/v1/groups/<id>/members/add/` | Admin JWT | Add member by phone |
| DELETE | `/api/v1/groups/<id>/members/<user_id>/remove/` | Admin JWT | Remove member |
| POST | `/api/v1/groups/<id>/leave/` | Member JWT | Leave group |
| GET | `/api/v1/groups/<id>/products/` | Member JWT | List shared products |
| POST | `/api/v1/groups/<id>/products/` | Member JWT | Share a product |
| POST | `/api/v1/groups/<id>/products/<sp_id>/finalize/` | Admin JWT | Finalize a product |

---

## Business Rules

| Rule | Detail |
|------|--------|
| Creator is admin | Auto-assigned on group creation |
| Only admin adds/removes members | Non-admins get 403 |
| Vendor groups — follower check | User must follow the store to be added |
| Customer groups — any NearKart user | Just needs an active account |
| Creator cannot leave | Must delete the group instead |
| Any member can share products | Product must be active + visible |
| Only admin can finalize | Marks a shared product as the group's final choice |
| Cannot finalize twice | Returns 400 if already finalized |

---

## Files Changed

| File | Change |
|------|--------|
| `apps/groups/models.py` | Group, GroupMember, GroupSharedProduct models |
| `apps/groups/services.py` | GroupService — create, add/remove member, share, finalize |
| `apps/groups/serializers.py` | Create, member, shared product serializers |
| `apps/groups/views.py` | 7 views |
| `apps/groups/urls.py` | 10 URL patterns |
| `apps/groups/admin.py` | Group + SharedProduct admin |
| `apps/groups/migrations/0001_initial.py` | Creates groups, group_members, group_shared_products tables |
