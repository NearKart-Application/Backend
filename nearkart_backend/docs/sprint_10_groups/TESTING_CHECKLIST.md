# Sprint 10 — Testing Checklist

**Verified on:** 2026-05-15
**Environment:** Docker local, dev mode

---

## Create Group

- [ ] POST `/groups/` `{"name": "Weekend Shopping", "group_type": "customer"}` with any JWT → 201
- [ ] Response has: `id`, `name`, `group_type`, `member_count: 1`, `created_by_name`
- [ ] POST `{"name": "VIP Followers", "group_type": "vendor"}` with vendor JWT → 201, `store_name` populated
- [ ] POST `group_type: vendor` with customer JWT → 400 — Only vendors can create vendor groups
- [ ] POST `group_type: vendor` with vendor who has no store → 400 — Create a store first
- [ ] POST without auth → 401

## List My Groups

- [ ] GET `/groups/` with JWT → array of groups user is member of
- [ ] After creating a group, it appears in the list with `member_count: 1`
- [ ] GET without auth → 401

## Group Detail

- [ ] GET `/groups/<id>/` with member token → 200, includes `members` array
- [ ] Creator appears in members with `role: admin`
- [ ] GET with non-member token → 404
- [ ] GET without auth → 401

## Add Member

- [ ] POST `/groups/<id>/members/add/` `{"phone_number": "+919876543210"}` with admin token → 201
- [ ] Member now appears in group detail
- [ ] POST with non-admin token → 403 — Only group admin can add members
- [ ] POST with phone of non-existent user → 404 — No active user found
- [ ] POST to add already-existing member → 400 — already a member
- [ ] POST to vendor group with non-follower phone → 403 — User does not follow this store
- [ ] POST to vendor group with follower phone → 201

## Remove Member

- [ ] DELETE `/groups/<id>/members/<user_id>/remove/` with admin token → 200
- [ ] Removed user no longer in members list
- [ ] DELETE with non-admin token → 403
- [ ] DELETE with wrong user_id → 404
- [ ] DELETE the group creator → 400 — Cannot remove the group creator

## Leave Group

- [ ] POST `/groups/<id>/leave/` with member token → 200 — You have left the group
- [ ] User no longer in member list
- [ ] POST leave as group creator → 400 — Group creator cannot leave
- [ ] POST leave as non-member → 400 — You are not a member

## Delete Group

- [ ] DELETE `/groups/<id>/` with creator token → 200 — Group deleted
- [ ] Group no longer appears in list (is_active=False)
- [ ] DELETE with non-creator member → 403 — Only the group creator can delete
- [ ] DELETE without auth → 401

## Share Product

- [ ] POST `/groups/<id>/products/` `{"product_id": "...", "note": "Looks great!"}` with member token → 201
- [ ] Response has: `product_name`, `product_price`, `store_name`, `shared_by_name`, `note`, `is_finalized: false`
- [ ] POST with invalid/inactive product_id → 400 — Product not found or not available
- [ ] POST with non-member token → 404
- [ ] POST without auth → 401

## List Shared Products

- [ ] GET `/groups/<id>/products/` with member token → array of shared products
- [ ] Finalized products appear first in list
- [ ] GET with non-member token → 404

## Finalize Product

- [ ] POST `/groups/<id>/products/<sp_id>/finalize/` with admin token → 200
- [ ] Response has `is_finalized: true`, `finalized_by_name` populated
- [ ] POST finalize already-finalized product → 400 — Product is already finalized
- [ ] POST finalize with non-admin token → 403 — Only group admin can finalize
- [ ] POST with wrong sp_id → 404

## Admin

- [ ] Group visible at http://localhost:8000/admin/groups/group/
- [ ] Can filter by group_type, is_active
- [ ] Inline shows group members
- [ ] SharedProduct visible at http://localhost:8000/admin/groups/groupsharedproduct/
- [ ] Can filter by is_finalized
