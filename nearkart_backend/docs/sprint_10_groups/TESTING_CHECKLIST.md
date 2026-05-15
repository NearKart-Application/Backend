# Sprint 10 — Testing Checklist

**Verified on:** 2026-05-15
**Environment:** Docker local, dev mode

---

## Profile ID — User Search

- [ ] GET `/auth/me/` → response includes `profile_id` field (e.g. `NK-A3X9K2`)
- [ ] GET `/auth/users/search/?profile_id=NK-XXXXXXXX` with valid profile_id → 200, returns `id`, `profile_id`, `full_name` (no phone)
- [ ] GET `/auth/users/search/?profile_id=NK-ZZZZZZZZ` (wrong id) → 404 — No user found with this Profile ID
- [ ] GET `/auth/users/search/` with no param → 400 — profile_id query param is required
- [ ] GET without auth → 401

---

## Create Group

- [ ] POST `/groups/` `{"name": "Weekend Shopping", "group_type": "customer"}` with any JWT → 201
- [ ] Response has: `id`, `name`, `group_type`, `member_count: 1`, `created_by_name`, `created_by_profile_id`
- [ ] Response does NOT contain any phone_number field
- [ ] POST `{"name": "VIP Followers", "group_type": "vendor"}` with vendor JWT → 201, `store_name` populated
- [ ] POST `group_type: vendor` with customer JWT → 400 — Only vendors can create vendor groups
- [ ] POST `group_type: vendor` with vendor who has no store → 400 — Create a store first
- [ ] POST without auth → 401

---

## List My Groups

- [ ] GET `/groups/` with JWT → array of groups user is member of
- [ ] After creating a group, it appears in the list with `member_count: 1`
- [ ] GET without auth → 401

---

## Group Detail

- [ ] GET `/groups/<id>/` with member token → 200, includes `members` array
- [ ] Creator appears in members with `role: admin`
- [ ] Each member has `profile_id` and `full_name` (no phone)
- [ ] GET with non-member token → 404
- [ ] GET without auth → 401

---

## Add Member — Customer Group (by Profile ID)

- [ ] POST `/groups/<id>/members/add/` `{"profile_id": "NK-XXXXXXXX"}` with admin token → 201
- [ ] Member now appears in group detail with their name + profile_id
- [ ] POST with non-admin token → 403 — Only group admin can add members
- [ ] POST with wrong profile_id → 404 — No user found with this Profile ID
- [ ] POST to add already-existing member → 400 — already a member
- [ ] POST without profile_id or user_id → 400 — Provide either profile_id or user_id

---

## Add Member — Vendor Group (from eligible members)

- [ ] GET `/groups/<id>/eligible-members/` with vendor admin token → list of followers not yet in group
- [ ] Each entry has `user_id`, `profile_id`, `full_name` (no phone)
- [ ] GET eligible-members on customer group → 400 — Eligible members only available for vendor groups
- [ ] GET eligible-members with non-admin token → 403
- [ ] POST `/groups/<id>/members/add/` `{"user_id": "<uuid>"}` with admin token → 201
- [ ] POST to add non-follower user_id to vendor group → 403 — User does not follow this store

---

## Remove Member

- [ ] DELETE `/groups/<id>/members/<user_id>/remove/` with admin token → 200
- [ ] Removed user no longer in members list
- [ ] DELETE with non-admin token → 403
- [ ] DELETE with wrong user_id → 404
- [ ] DELETE the group creator → 400 — Cannot remove the group creator

---

## Make Admin / Remove Admin

- [ ] POST `/groups/<id>/members/<user_id>/make-admin/` with admin token → 200 — user is now an admin
- [ ] Promoted user appears with `role: admin` in group detail
- [ ] POST make-admin on already-admin user → 400 — User is already an admin
- [ ] POST make-admin with non-admin token → 403 — Only group admin can promote members
- [ ] POST `/groups/<id>/members/<user_id>/remove-admin/` with admin token → 200 — user demoted
- [ ] POST remove-admin on group creator → 400 — Cannot remove admin role from the group creator
- [ ] POST remove-admin on non-admin member → 400 — User is not an admin

---

## Leave Group

- [ ] POST `/groups/<id>/leave/` with member token → 200 — You have left the group
- [ ] User no longer in member list
- [ ] POST leave as group creator → 400 — Group creator cannot leave
- [ ] POST leave as non-member → 400 — You are not a member

---

## Delete Group

- [ ] DELETE `/groups/<id>/` with creator token → 200 — Group deleted
- [ ] Group no longer appears in list (is_active=False)
- [ ] DELETE with non-creator member → 403 — Only the group creator can delete
- [ ] DELETE without auth → 401

---

## Share Product

- [ ] POST `/groups/<id>/products/` `{"product_id": "...", "note": "Looks great!"}` → 201
- [ ] Response has: `product_name`, `product_price`, `store_name`, `shared_by_name`, `shared_by_profile_id`, `note`, `is_finalized: false`
- [ ] Response does NOT contain phone_number
- [ ] POST with `note` containing external URL (e.g. `http://youtube.com/xyz`) → 400 — External links are not allowed
- [ ] POST with `note` containing `nearkart://product/123` → 201 (allowed)
- [ ] POST with invalid/inactive product_id → 400 — Product not found or not available
- [ ] POST with non-member token → 404
- [ ] POST without auth → 401

---

## List Shared Products

- [ ] GET `/groups/<id>/products/` with member token → array of shared products
- [ ] Finalized products appear first in list
- [ ] GET with non-member token → 404

---

## Finalize Product

- [ ] POST `/groups/<id>/products/<sp_id>/finalize/` with admin token → 200
- [ ] Response has `is_finalized: true`, `finalized_by_name` populated
- [ ] POST finalize already-finalized product → 400 — Product is already finalized
- [ ] POST finalize with non-admin token → 403 — Only group admin can finalize
- [ ] POST with wrong sp_id → 404

---

## Django Admin

- [ ] Group visible at http://localhost:8000/admin/groups/group/
- [ ] Can filter by group_type, is_active
- [ ] Inline shows group members with roles
- [ ] SharedProduct visible at http://localhost:8000/admin/groups/groupsharedproduct/
- [ ] Can filter by is_finalized
