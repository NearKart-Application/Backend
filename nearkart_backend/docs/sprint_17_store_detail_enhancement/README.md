# Sprint 17 — Store Detail Enhancement

## What was built

Wired the Reviews & Ratings system (built in Sprint 16) into `StoreDetailScreen` and cleaned up the old inline review form.

### Business rules
- Customer taps "✍ Write Review" on StoreDetailScreen → navigates to `WriteReviewScreen` (reservation-gated, same as from Reservations flow)
- StoreDetailScreen shows a 3-review preview with vendor replies visible
- "See all N reviews →" button navigates to `StoreReviewsScreen` (full rating breakdown + all reviews)
- Backend-computed `rating` and `review_count` are live (re-fetched on every store detail load)

---

## Mobile changes

| File | Change |
|------|--------|
| `ui/screens/store/StoreDetailScreen.kt` | Added `onWriteReview` and `onSeeAllReviews` callbacks; removed inline review form; added "See all N reviews →" button; updated `StoreReviewCard` to display vendor replies |
| `ui/screens/store/StoreDetailViewModel.kt` | Removed `submitReview()`, `isSubmittingReview`, `reviewSuccess`, `reviewError`, and their clear functions |
| `MainActivity.kt` | Wired `onWriteReview` and `onSeeAllReviews` on the `STORE_DETAIL` route |

---

## No new API endpoints

All endpoints were built in Sprint 16. Sprint 17 is purely a mobile navigation and UI wiring sprint.

---

## User flow (updated)

### Customer views and writes a review from StoreDetail
1. Open any store → scroll to Reviews section
2. See avg rating + preview of last 3 reviews (with vendor replies shown in green)
3. Tap "See all N reviews →" → full `StoreReviewsScreen` with rating bars
4. Tap "✍ Write Review" → `WriteReviewScreen` (reservation-gate enforced server-side)
5. Submit → navigates back to StoreDetail, which refreshes on next load

---

## What changed vs Sprint 16

In Sprint 16 the "Write a Review" entry point was only accessible from Reservations. Sprint 17 adds a second entry point from StoreDetailScreen, making reviews discoverable from the store browsing flow.
