# NearKart — Project Overview

## Does Docker show the Frontend?

NO. Docker in this project runs ONLY the Backend.

```
What Docker runs (this repo):        What is NOT in Docker yet:
─────────────────────────────        ──────────────────────────
Django REST API      :8000           Customer Mobile App  (Sprint 9)
WebSocket (Daphne)   :8001           Vendor Mobile App    (Sprint 10)
PostgreSQL           :5432           Vendor Web Dashboard (Sprint 11)
Redis                :6379
Celery Worker
Celery Beat (cron)
Nginx                :80
```

The frontend apps (React Native + React Web) are separate projects
built in later sprints. Right now you can only test via:
- Postman (API calls)
- Swagger UI at http://localhost:8000/api/docs/
- Django Admin at http://localhost:8000/admin/

---

## Full Project Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NEARKART PLATFORM                     │
├──────────────────────────────────────────────────────────┤
│         Android App (Kotlin + Jetpack Compose)           │
│   Customer + Vendor — single APK, role-based UI          │
│   Sprints 1–18 complete · release/v1.0                   │
└──────────────────────────┬───────────────────────────────┘
                            │  REST API + WebSocket
                            ▼
         ┌──────────────────────────────────────┐
         │         BACKEND (This Repo)           │
         │                                      │
         │  Django REST API  ← You are here     │
         │  Channels (WS)                       │
         │  Celery (Tasks)                      │
         ├──────────────────────────────────────┤
         │  PostgreSQL + PostGIS                │
         │  Redis                               │
         │  AWS S3 (videos/images)              │
         │  Twilio (SMS OTP)                    │
         │  Firebase (Push notifications)       │
         │  Razorpay (Payments)                 │
         └──────────────────────────────────────┘
```

---

## Sprint Roadmap

| Sprint | Module | Status | Folder |
|--------|--------|--------|--------|
| S0 | Environment Setup | Done ✅ | `docs/sprint_0_environment/` |
| S1 | Django Foundation | Done ✅ | `docs/sprint_1_django_foundation/` |
| S2 | Auth Module | Done ✅ | `docs/sprint_2_auth_module/` |
| S3 | Store + Product | Done ✅ | `docs/sprint_3_store_product/` |
| S4 | Video Module | Done ✅ | `docs/sprint_4_video/` |
| S5 | Chat (WebSocket) | Done ✅ | `docs/sprint_5_chat/` |
| S6 | Blacklist Engine | Done ✅ | `docs/sprint_6_blacklist/` |
| S7 | Billing + Wallet | Done ✅ | `docs/sprint_7_billing/` |
| S8 | Analytics + Admin | Done ✅ | `docs/sprint_8_analytics/` |
| S9 | Reservations | Done ✅ | `docs/sprint_9_reservations/` |
| S10 | Groups | Done ✅ | `docs/sprint_10_groups/` |
| S11 | Notifications | Done ✅ | `docs/sprint_11_notifications/` |
| S12 | Staging + Production + Razorpay | Done ✅ | `docs/sprint_12_production/` |
| S13 | Performance Algorithms + Test Infrastructure | Done ✅ | `docs/sprint_13_tests/` |
| S14 | FCM Device Tokens + Notification Device API _(mobile-driven)_ | Done ✅ | — |
| S15 | Loyalty Points + Referral System | Done ✅ | `apps/loyalty/` · `apps/reservations/` (loyalty fields) |
| S16 | Reviews & Ratings | Done ✅ | `apps/stores/` (vendor reply, reservation gate, 3 new endpoints) |
| S17 | Store Detail Enhancement _(mobile-driven)_ | Done ✅ | — |
| S18 | Rating Badges + Pull-to-Refresh | Done ✅ | `apps/products/` (serializers) · `docs/sprint_18_ratings_refresh/` |
| S19 | Search Filters + Sort · Follow Feed · Vendor Invoices · Map Enhancements | Done ✅ | `apps/products/` · `apps/stores/` · `docs/sprint_19_search_filters_follow_invoices_map/` |
| S20 | Admin Panel · NS Code System (NSC/NSB prefixes + Option C regeneration) · User Suspension · Activity Log · Video Deletion · Create User · Search by NS Code | Done ✅ | `apps/admin_panel/` · `apps/auth_app/` · `core/utils/codes.py` · `docs/sprint_20_admin_panel/` |
| S21 | Admin Category Management · Admin Offer Template Management · Vendor template chip integration (API-driven, default auto-select) | Done ✅ | `apps/admin_panel/` · `apps/products/` · `apps/stores/` · `docs/sprint_21_admin_categories_offer_templates/` |
| S23 | Store Hours API wiring · Vendor Discount Code CRUD + customer apply flow · Product image gallery with per-image delete | Done ✅ | `apps/stores/` · `apps/products/` · `docs/sprint_23_store_hours_discounts_gallery/` |
| S25 | `active_offer_labels` in nearby stores response · Offer expiry filter · Cache bust on offer changes · `sale_price` PATCH → variant price · seed_city_offers (197K offers) · seed_city_broadcast_posts (131K posts) | Done ✅ | `apps/stores/` · `apps/products/` · `core/utils/` · `docs/sprint_25_map_integration/` |
| S26 | Structured Product ID — `NS-{ShopAbbr}-{LocalityCode}-{CategoryCode}-{Unique}` · `_store_abbreviation()` (clash-safe initials) · `_locality_code()` · `_CATEGORY_CODES` table · `generate-code` accepts `?category=` | Done ✅ | `apps/products/services.py` · `apps/products/views.py` · `docs/sprint_26_product_id_system/` |
