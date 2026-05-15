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
├──────────────────┬──────────────────┬───────────────────┤
│  Customer App    │   Vendor App     │  Vendor Web       │
│  (React Native)  │  (React Native)  │  Dashboard        │
│   Sprint 9       │   Sprint 10      │  (React + Vite)   │
│                  │                  │   Sprint 11       │
└────────┬─────────┴────────┬─────────┴────────┬──────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
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
