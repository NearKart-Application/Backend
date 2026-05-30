# Sprint 17 — Testing Checklist

## StoreDetailScreen — Reviews section

- [ ] Reviews section shows avg rating + review count next to "Reviews" heading
- [ ] Up to 3 preview reviews are shown (not 5 from old code)
- [ ] Store with 0 reviews shows "No reviews yet — be the first!" empty state
- [ ] Store with ≥1 review shows "See all N reviews →" button with correct count
- [ ] "See all N reviews →" tap navigates to StoreReviewsScreen for this store
- [ ] StoreReviewsScreen back button returns to StoreDetailScreen
- [ ] "✍ Write Review" tap navigates to WriteReviewScreen with correct storeId + storeName
- [ ] WriteReviewScreen back button returns to StoreDetailScreen
- [ ] Customer with NO completed reservation at this store → WriteReviewScreen shows 403 error on submit
- [ ] Customer with a completed reservation → review submits and navigates back successfully

## Vendor replies visible in preview

- [ ] Review with a vendor reply shows green "Vendor reply" block in StoreDetailScreen preview
- [ ] Review without a vendor reply shows no green block
- [ ] Vendor reply text wraps correctly on long content

## Navigation edge cases

- [ ] Open store A → "See all reviews" → back → open store B → "See all reviews" — shows store B's reviews (not cached from A)
- [ ] Open store A → "Write Review" → back → opens WriteReviewScreen for correct store on re-tap
- [ ] Deep navigation: Home → Store → See All Reviews → back × 2 → still on Home

## Regression checks

- [ ] Offers section still shows (S11 feature)
- [ ] Trending products horizontal scroll still works
- [ ] Category filter chips still work
- [ ] Follow / Unfollow button still works
- [ ] Chat button navigates to chat thread
- [ ] "🧭 Go" button opens maps
- [ ] Share button shows system share sheet
