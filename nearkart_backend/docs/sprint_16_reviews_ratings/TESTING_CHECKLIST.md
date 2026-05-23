# Sprint 16 — Testing Checklist

## Customer — Write a Review

- [ ] Customer with NO completed reservations: submit review → expect 403 `no_completed_reservation`
- [ ] Customer with a completed reservation: submit 5-star review + comment → 200, review appears in store list
- [ ] Submit review with missing rating → button disabled (rating = 0)
- [ ] Submit review with rating only (no comment) → success
- [ ] Second review from same customer at same store → upserts (replaces) existing review
- [ ] Rating bars on StoreReviewsScreen reflect correct distribution after submission

## Vendor — View & Reply

- [ ] Vendor Dashboard shows "Reviews" quick action tile
- [ ] VendorReviewsScreen loads all reviews for vendor's store
- [ ] Empty state shown when store has no reviews
- [ ] "Awaiting reply" count badge correct
- [ ] Tap "Reply" → dialog opens with review text preview
- [ ] Submit empty reply → "Post Reply" button disabled
- [ ] Submit valid reply → review card shows vendor reply in green block
- [ ] Re-reply to already-replied review updates the text
- [ ] Reply to non-existent review → graceful error

## Notifications

- [ ] Vendor receives FCM notification when customer submits a review
- [ ] Notification shows store name + star rating

## ReservationsScreen

- [ ] Active reservations do NOT show "Write a Review" button
- [ ] Cancelled/expired reservations do NOT show "Write a Review" button
- [ ] Completed reservations show "⭐ Write a Review" button
- [ ] Tapping "Write a Review" navigates to WriteReviewScreen with correct storeId + storeName
- [ ] After successful submission, navigates back to ReservationsScreen

## Edge Cases

- [ ] Review with 500-char comment: submits and displays correctly
- [ ] 501-char comment: input capped at 500 (UI level)
- [ ] Network error on submit: error message shown, state resets on retry
- [ ] StoreReviewsScreen with 0 reviews shows empty state message
