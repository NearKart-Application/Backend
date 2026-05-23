# NearKart Backend — Documentation Map

> One place to find every document, its file path, and what it contains.
> If you are looking for something, start here.

---

## Root Level Docs

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| This file | `docs/DOCS_MAP.md` | Master map of all documentation |
| Documentation Index | `docs/INDEX.md` | Sprint-by-sprint links to all docs |
| Project Overview | `docs/PROJECT_OVERVIEW.md` | Full architecture diagram, Docker services, sprint roadmap |
| **Application Pricing Summary** | `docs/APPLICATION_PRICING_SUMMARY.md` | Firebase, Maps, Twilio, AWS S3, Razorpay — monthly/annual cost estimates, limits, 3 launch scenarios |
| How to Run & Test | `docs/HOW_TO_RUN_AND_TEST.md` | Setup venv, run Docker, test via Postman/Swagger |
| Database Schema | `docs/DATABASE_SCHEMA.txt` | All table names, columns, and relationships |
| Screenshots | `docs/images/README.md` | Where to save test screenshots |

---

## Word Documents (Open in Microsoft Word / LibreOffice)

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Master API Testing Guide | `docs/NearKart_Master_API_Testing_Guide.docx` | All 90 API endpoints — step-by-step Postman testing, Sprint 1–15 |
| Complete Project Journey | `docs/NearKart_Complete_Project_Journey_Sprint0_to_Sprint12.docx` | Full project history Sprint 0–12, all models, decisions, architecture |
| Sprint 0–3 Reference | `docs/NearKart_Backend_Complete_Reference_Sprint0_to_Sprint3.docx` | Detailed reference for early sprints (Auth, Store, Product) |

---

## Generator Scripts (Recreate Word Docs)

| Script | File Path | What it generates |
|--------|-----------|------------------|
| API Guide generator | `docs/gen_api_guide.py` | Regenerates `NearKart_Master_API_Testing_Guide.docx` |
| Project Journey generator | `docs/gen_project_journey.py` | Regenerates `NearKart_Complete_Project_Journey_Sprint0_to_Sprint12.docx` |

Run with: `python3 docs/gen_api_guide.py` or `python3 docs/gen_project_journey.py`

---

## Sprint 0 — Environment Setup

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_0_environment/README.md` | Tools to install, accounts to create, Docker setup |

---

## Sprint 1 — Django Foundation

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_1_django_foundation/README.md` | Project structure, 7 Docker services, settings split |
| Code Reference | `docs/sprint_1_django_foundation/CODE_REFERENCE.md` | Key files explained — settings, urls, asgi, celery |
| API Test Flow | `docs/sprint_1_django_foundation/API_TEST_FLOW.md` | Health check endpoint, first API call walkthrough |

---

## Sprint 2 — Auth Module

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_2_auth_module/README.md` | OTP flow, JWT tokens, User model, dev mode OTP |
| Code Reference | `docs/sprint_2_auth_module/CODE_REFERENCE.md` | OTPService, JWTService, User model explained |
| Postman Guide | `docs/sprint_2_auth_module/POSTMAN_GUIDE.md` | Step-by-step: send OTP → verify → get token → use token |
| Testing Checklist | `docs/sprint_2_auth_module/TESTING_CHECKLIST.md` | All auth test cases — OTP send, verify, refresh, logout |
| API Test Flow | `docs/sprint_2_auth_module/API_TEST_FLOW.md` | Quick curl commands for auth flow |

---

## Sprint 3 — Store + Product

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_3_store_product/README.md` | Store model, Product model, geo location, Store Hours |
| Code Reference | `docs/sprint_3_store_product/CODE_REFERENCE.md` | Store/Product serializers, PostGIS DWithin queries |
| Postman Guide | `docs/sprint_3_store_product/POSTMAN_GUIDE.md` | Create store → add products → test nearby search |
| Testing Checklist | `docs/sprint_3_store_product/TESTING_CHECKLIST.md` | Store CRUD, product CRUD, geo search, store hours |
| API Test Flow | `docs/sprint_3_store_product/API_TEST_FLOW.md` | Quick curl commands for store/product flow |

---

## Sprint 4 — Video Module

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_4_video/README.md` | 2-step upload flow, HLS transcoding, 30-day expiry, download before delete |
| Code Reference | `docs/sprint_4_video/CODE_REFERENCE.md` | AWSService, VideoService, transcode_video task |
| Postman Guide | `docs/sprint_4_video/POSTMAN_GUIDE.md` | Request upload → confirm → feed → like → download |
| Testing Checklist | `docs/sprint_4_video/TESTING_CHECKLIST.md` | Upload flow, feed, likes, expiry, download endpoint |
| API Test Flow | `docs/sprint_4_video/API_TEST_FLOW.md` | Quick curl for video upload and feed |

---

## Sprint 5 — Chat (WebSocket)

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_5_chat/README.md` | WebSocket architecture, Conversation/Message models, channels |
| Code Reference | `docs/sprint_5_chat/CODE_REFERENCE.md` | ChatConsumer, routing, JWT WS auth |
| Postman Guide | `docs/sprint_5_chat/POSTMAN_GUIDE.md` | Create conversation → connect WS → send/receive messages |
| Testing Checklist | `docs/sprint_5_chat/TESTING_CHECKLIST.md` | REST endpoints + WebSocket connect/message/disconnect |
| API Test Flow | `docs/sprint_5_chat/API_TEST_FLOW.md` | wscat commands for WebSocket testing |

---

## Sprint 6 — Blacklist Engine

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_6_blacklist/README.md` | Inactivity enforcement, warning flow, blacklist/unblacklist |
| Postman Guide | `docs/sprint_6_blacklist/POSTMAN_GUIDE.md` | Check status → trigger warning → blacklist flow |
| Testing Checklist | `docs/sprint_6_blacklist/TESTING_CHECKLIST.md` | Blacklist status, vendor access blocked, admin override |

---

## Sprint 7 — Billing + Wallet

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_7_billing/README.md` | Plans (free/basic/premium), wallet top-up, subscription, limits |
| Postman Guide | `docs/sprint_7_billing/POSTMAN_GUIDE.md` | List plans → top-up → subscribe → check status |
| Testing Checklist | `docs/sprint_7_billing/TESTING_CHECKLIST.md` | Wallet, subscription, plan limits, expiry task |

---

## Sprint 8 — Analytics + Admin Panel

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_8_analytics/README.md` | Vendor analytics dashboard, admin panel for staff |
| Postman Guide | `docs/sprint_8_analytics/POSTMAN_GUIDE.md` | Vendor dashboard → store stats → admin user management |
| Testing Checklist | `docs/sprint_8_analytics/TESTING_CHECKLIST.md` | Analytics endpoints, admin-only access, staff user creation |

---

## Sprint 9 — Reservations

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_9_reservations/README.md` | Reservation state machine, 2-hour hold, auto-expire |
| Postman Guide | `docs/sprint_9_reservations/POSTMAN_GUIDE.md` | Create → confirm → cancel → expire flow |
| Testing Checklist | `docs/sprint_9_reservations/TESTING_CHECKLIST.md` | All state transitions, vendor/customer views, expiry task |

---

## Sprint 10 — Groups

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_10_groups/README.md` | Profile ID system, public/private groups, product sharing |
| Postman Guide | `docs/sprint_10_groups/POSTMAN_GUIDE.md` | Create group → add members → share product → finalize |
| Testing Checklist | `docs/sprint_10_groups/TESTING_CHECKLIST.md` | All 14 endpoints, privacy rules, group WebSocket |

---

## Sprint 11 — Notifications

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_11_notifications/README.md` | 18 notification types, FCM push, in-app inbox, Celery tasks |
| Postman Guide | `docs/sprint_11_notifications/POSTMAN_GUIDE.md` | Register device token → trigger events → check inbox |
| Testing Checklist | `docs/sprint_11_notifications/TESTING_CHECKLIST.md` | All notification types, mark read, unread count, bulk mark |

---

## Sprint 12 — Production + Razorpay + Video Expiry

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_12_production/README.md` | Production settings, Razorpay flow, video expiry/download feature |
| Postman Guide | `docs/sprint_12_production/POSTMAN_GUIDE.md` | Razorpay payment steps + video download endpoint |
| Testing Checklist | `docs/sprint_12_production/TESTING_CHECKLIST.md` | Production settings, Razorpay, video expiry, CI/CD, Django Admin |
| Deploy Checklist | `docs/sprint_12_production/DEPLOY_CHECKLIST.md` | Pre-deploy checks, deploy steps, post-deploy verification, rollback |
| **Going to Production** | `docs/sprint_12_production/GOING_TO_PRODUCTION.md` | **Every dummy value to replace — all 6 dev bypasses, all services** |

---

## Sprint 13 — Performance + Tests

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Sprint README | `docs/sprint_13_tests/README.md` | Performance algorithms added, test infrastructure overview |
| Postman Guide | `docs/sprint_13_tests/POSTMAN_GUIDE.md` | How to verify algorithm outputs via API |
| Testing Checklist | `docs/sprint_13_tests/TESTING_CHECKLIST.md` | Unit + integration + load test checklist |
| **Test Runner Guide** | `docs/sprint_13_tests/TEST_RUNNER_GUIDE.md` | How to install, run all/single/keyword tests, coverage reports, markers, CI replication, dev-mode bypass explanations |
| **Server Capability** | `docs/sprint_13_tests/SERVER_CAPABILITY.md` | Concurrent user capacity, layer-by-layer breakdown, cache hit rates, configuration reference, scaling roadmap to 25k+ users, monitoring commands |
| **Load Test Results** | `docs/sprint_13_tests/LOAD_TEST_RESULTS.md` | Smoke/load/stress test results (50/200/500 users), before vs after comparison, PgBouncer/Redis metrics, bugs found and fixed, how to re-run |

---

## Sprint 14 — FCM Push Notifications + Notification Improvements  _(mobile-driven)_

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Mobile Sprint README | _(mobile repo)_ `docs/sprint_14_notifications_profile_qr/README.md` | FCM service wiring, edit profile screen, QR scanner screen |
| Mobile Testing Checklist | _(mobile repo)_ `docs/sprint_14_notifications_profile_qr/TESTING_CHECKLIST.md` | FCM token registration, profile edit, QR code scan flow |
| Mobile Postman Guide | _(mobile repo)_ `docs/sprint_14_notifications_profile_qr/POSTMAN_GUIDE.md` | Device token API, profile update API |

---

## Sprint 15 — Loyalty Points + Referral System

| Document | File Path | What it contains |
|----------|-----------|-----------------|
| Mobile Sprint README | _(mobile repo)_ `docs/sprint_15_loyalty_referral/README.md` | Full loyalty system — backend + mobile screens, business rules |
| Mobile Testing Checklist | _(mobile repo)_ `docs/sprint_15_loyalty_referral/TESTING_CHECKLIST.md` | Balance, referral, redemption, reservation discount test cases |
| Mobile Postman Guide | _(mobile repo)_ `docs/sprint_15_loyalty_referral/POSTMAN_GUIDE.md` | All 5 loyalty endpoints with request/response examples |

---

## Quick Reference — "Where do I find...?"

| I want to know... | Go to |
|-------------------|-------|
| How to run the project locally | `docs/HOW_TO_RUN_AND_TEST.md` |
| Full architecture diagram | `docs/PROJECT_OVERVIEW.md` |
| Monthly / annual infrastructure costs | `docs/APPLICATION_PRICING_SUMMARY.md` |
| Service limits (Maps, Twilio, Razorpay…) | `docs/APPLICATION_PRICING_SUMMARY.md` |
| All 90 API endpoints in one place | `docs/NearKart_Master_API_Testing_Guide.docx` |
| The whole project story Sprint 0–12 | `docs/NearKart_Complete_Project_Journey_Sprint0_to_Sprint12.docx` |
| How OTP login works | `docs/sprint_2_auth_module/README.md` |
| How to test Auth in Postman | `docs/sprint_2_auth_module/POSTMAN_GUIDE.md` |
| How video upload works | `docs/sprint_4_video/README.md` |
| How to download a video before it expires | `docs/sprint_12_production/POSTMAN_GUIDE.md` |
| How Razorpay payment works | `docs/sprint_12_production/README.md` |
| How WebSocket/Chat works | `docs/sprint_5_chat/README.md` |
| How billing/subscriptions work | `docs/sprint_7_billing/README.md` |
| How groups work | `docs/sprint_10_groups/README.md` |
| All notification types | `docs/sprint_11_notifications/README.md` |
| What to change before going live | `docs/sprint_12_production/GOING_TO_PRODUCTION.md` |
| How to deploy to production | `docs/sprint_12_production/DEPLOY_CHECKLIST.md` |
| All database tables | `docs/DATABASE_SCHEMA.txt` |
| How to run the test suite | `docs/sprint_13_tests/TEST_RUNNER_GUIDE.md` |
| How many users the server can handle | `docs/sprint_13_tests/SERVER_CAPABILITY.md` |
| How to scale beyond 10,000 users | `docs/sprint_13_tests/SERVER_CAPABILITY.md` |
| Load test results and pass/fail status | `docs/sprint_13_tests/LOAD_TEST_RESULTS.md` |
| How loyalty points work | _(mobile repo)_ `docs/sprint_15_loyalty_referral/README.md` |
| How referral codes work | _(mobile repo)_ `docs/sprint_15_loyalty_referral/README.md` |
| Loyalty API endpoints (Postman) | _(mobile repo)_ `docs/sprint_15_loyalty_referral/POSTMAN_GUIDE.md` |
| FCM push notification setup | _(mobile repo)_ `docs/sprint_14_notifications_profile_qr/README.md` |
