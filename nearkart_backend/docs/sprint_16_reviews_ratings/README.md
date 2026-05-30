# Sprint 16 — Reviews & Ratings

## What was built

Customer-facing reviews and vendor reply system, end-to-end.

### Business Rules
- Only customers with **at least one completed reservation** at a store may submit a review
- One review per customer per store (upsert — editing replaces the previous review)
- Rating: 1–5 stars (required) + text comment (optional, max 500 chars)
- Vendor can reply once per review (reply is editable via re-posting)
- Reviews are public (no auth needed to read)
- Vendor receives an FCM push notification when a new review arrives

---

## Backend changes

| File | Change |
|------|--------|
| `apps/stores/models.py` | Added `vendor_reply` (TextField) and `vendor_reply_at` (DateTimeField) to `StoreReview` |
| `apps/stores/serializers.py` | Updated `StoreReviewSerializer` + `StoreReviewListSerializer` to expose vendor reply fields; added `VendorReplySerializer` |
| `apps/stores/views.py` | Added reservation-gating to `StoreReviewView.post()`; added `VendorReviewReplyView`, `VendorReviewsListView`, `MyReviewsView` |
| `apps/stores/urls.py` | Added 3 new URL patterns |
| `apps/stores/migrations/0004_storereview_vendor_reply.py` | Migration for new fields |
| `apps/notifications/services.py` | Added `notify_new_review()` |

### New API Endpoints (Sprint 16)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET`  | `/stores/mine/reviews/` | Customer JWT | My reviews (customer) |
| `GET`  | `/stores/{id}/reviews/vendor/` | Vendor JWT (owner) | All reviews for my store |
| `POST` | `/stores/{id}/reviews/{reviewId}/reply/` | Vendor JWT (owner) | Reply to a review |

### Existing endpoints enhanced

| Endpoint | Enhancement |
|----------|-------------|
| `POST /stores/{id}/reviews/` | Now gates on completed reservation + sends vendor notification |
| `GET /stores/{id}/reviews/` | Now returns `vendor_reply` and `vendor_reply_at` |

---

## Mobile changes

| File | Change |
|------|--------|
| `data/models/StoreModels.kt` | Added `vendorReply`, `vendorReplyAt`, `storeId`, `storeName` to `Review`; added `VendorReplyRequest`, `ReviewListResponse` |
| `data/api/StoreApiService.kt` | Added `getVendorReviews`, `replyToReview`, `getMyReviews` endpoints |
| `data/repository/StoreRepository.kt` | Added `getVendorReviews`, `replyToReview`, `getMyReviews` methods |
| `ui/screens/reviews/WriteReviewScreen.kt` | New screen — star picker + comment + submit |
| `ui/screens/reviews/WriteReviewViewModel.kt` | New ViewModel |
| `ui/screens/reviews/StoreReviewsScreen.kt` | New screen — summary card + rating bars + review list with vendor replies |
| `ui/screens/reviews/StoreReviewsViewModel.kt` | New ViewModel |
| `ui/screens/vendor/VendorReviewsScreen.kt` | New screen — vendor sees all reviews, can tap Reply |
| `ui/screens/vendor/VendorReviewsViewModel.kt` | New ViewModel |
| `ui/screens/reservations/ReservationsScreen.kt` | Added `onWriteReview` callback + "⭐ Write a Review" button on completed reservations |
| `ui/screens/vendor/VendorDashboardScreen.kt` | Added "Reviews" quick action tile |
| `ui/navigation/NavGraph.kt` | Added `VENDOR_REVIEWS`, `WRITE_REVIEW`, `STORE_REVIEWS` routes |
| `MainActivity.kt` | Wired all 3 new composable destinations |

---

## User flows

### Customer writes a review
1. Go to Reservations → Past section
2. Tap "⭐ Write a Review" on a completed reservation
3. Select 1–5 stars, optionally type a comment
4. Tap "Submit Review" → success navigates back

### Customer views store reviews
- Navigable via `Routes.storeReviews(storeId, storeName)` (wired from store detail in a future sprint)

### Vendor replies to a review
1. Vendor Dashboard → "Reviews" quick action
2. See all reviews with unreplied count badge
3. Tap "Reply" under any review
4. Type reply in dialog → Post
