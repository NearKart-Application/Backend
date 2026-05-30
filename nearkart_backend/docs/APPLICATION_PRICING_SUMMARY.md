# NearKart — Application Pricing Summary

> Last updated: 2026-05-23  
> All USD prices converted at ₹83 = $1 where noted.  
> Estimates assume a **small-to-medium Indian startup** (launching in 1–3 cities, 0–10 K active users).

---

## 1. Firebase (FCM Push Notifications)

| Item | Free Tier | Pay-as-you-go | Monthly Est. | Annual Est. |
|------|-----------|---------------|-------------|-------------|
| Cloud Messaging (FCM) | **Unlimited** messages | Free forever | **$0** | **$0** |
| Firebase Analytics | Unlimited | Free forever | $0 | $0 |
| Firebase Hosting (optional) | 10 GB storage / 10 GB/month transfer | $0.026/GB storage, $0.15/GB transfer | $0 | $0 |

**Plan needed:** Spark (Free plan) — sufficient for FCM + Analytics.  
**Hard limits:** None for push notifications. Hosting free tier resets monthly.  
**Trigger for paid tier:** Only if you add Firestore / Realtime DB / Cloud Functions — not needed for current architecture.

---

## 2. Google Maps Platform

| API | Free Monthly Credit | Unit Price (beyond credit) | Monthly Est. | Annual Est. |
|-----|--------------------|-----------------------------|-------------|-------------|
| **$200 credit** (auto-applied) | $200/month | — | — | — |
| Maps SDK for Android | **Free** (no per-load fee on mobile) | Free | **$0** | **$0** |
| Geocoding API | Covered by credit | $5 / 1,000 requests | ~$0 | ~$0 |
| Places API (Nearby Search) | Covered by credit | $17 / 1,000 requests | ~$0 | ~$0 |
| Directions API (optional) | Covered by credit | $5 / 1,000 requests | ~$0 | ~$0 |

**Key limit:** $200/month free credit covers ~11,700 Geocoding calls or ~11,700 Places calls per month.  
**At 10,000 MAU** (est. 3 API calls/session): ~30,000 calls/month → $150 → still within credit.  
**Break-even scale:** ~40,000 monthly API calls → first overage charge appears.  
**Billing required:** Yes, you must add a billing account, but charges only apply beyond $200 credit.

---

## 3. Twilio (SMS OTP)

| Item | Cost | Notes |
|------|------|-------|
| Outbound SMS — India | ~$0.0085 / SMS | A2P carrier surcharges included |
| Phone number rental | ~$1.15 / month | US virtual number; Indian DLT registration extra |
| India DLT registration (one-time) | ~₹10,000–₹25,000 | Required by TRAI for bulk OTP in India |
| Free trial credit | $15.50 | One-time on account creation |

### Volume-based monthly estimate

| OTPs / Month | SMS Cost | Number Cost | **Monthly Total** | **Annual Total** |
|-------------|----------|-------------|-------------------|-----------------|
| 500 | $4.25 | $1.15 | **$5.40** (~₹448) | **$64.80** (~₹5,379) |
| 1,000 | $8.50 | $1.15 | **$9.65** (~₹801) | **$115.80** (~₹9,611) |
| 5,000 | $42.50 | $1.15 | **$43.65** (~₹3,623) | **$523.80** (~₹43,475) |
| 10,000 | $85.00 | $1.15 | **$86.15** (~₹7,150) | **$1,033.80** (~₹85,805) |
| 50,000 | $425.00 | $1.15 | **$426.15** (~₹35,370) | **$5,113.80** (~₹424,445) |

**Hard limits:** Default 1 message/second throughput (can be raised by request).  
**Tip:** Enable OTP re-use window (e.g. 5 min cooldown) to reduce SMS count.

---

## 4. AWS S3 (Images & Videos)

| Item | Price | Free Tier (12 months) |
|------|-------|-----------------------|
| Storage (Standard) | $0.023 / GB / month | 5 GB |
| Data Transfer OUT | $0.09 / GB | 15 GB / month |
| PUT / COPY / POST requests | $0.005 / 1,000 | 2,000 requests |
| GET / SELECT requests | $0.0004 / 1,000 | 20,000 requests |
| CloudFront CDN (optional) | $0.0085 / GB (first 10 TB) | 1 TB / month (12 months) |

### Storage & transfer monthly estimate

| Scale | Storage | Transfer Out | PUT Requests | **Monthly Total** | **Annual Total** |
|-------|---------|--------------|-------------|-------------------|-----------------|
| Early (5 GB, 20 GB out) | $0.12 | $1.80 | $0.05 | **~$2** (~₹166) | **~$24** (~₹1,992) |
| Small (20 GB, 50 GB out) | $0.46 | $4.50 | $0.25 | **~$5** (~₹415) | **~$60** (~₹4,980) |
| Medium (100 GB, 300 GB out) | $2.30 | $27.00 | $1.00 | **~$30** (~₹2,490) | **~$360** (~₹29,880) |
| Large (500 GB, 1 TB out) | $11.50 | $90.00 | $2.50 | **~$104** (~₹8,632) | **~$1,248** (~₹1,03,584) |

**Hard limits:** No storage cap; single object max 5 TB.  
**Tip:** Enable S3 Lifecycle rules to move old videos to S3 Glacier (~$0.004/GB) to cut costs.

---

## 5. Razorpay (Payment Gateway)

| Plan | Monthly Fee | Per Transaction | Settlement |
|------|------------|-----------------|------------|
| Standard | ₹0 | **2% + 18% GST** (effective ~2.36%) | T+2 business days |
| Route (Marketplace) | ₹0 | 2% + GST | T+2 |
| Subscription billing | ₹0 | 2% + GST per renewal | T+2 |

### Fee estimate by GMV

| Monthly GMV | Razorpay Fee (2.36%) | **Monthly Cost** | **Annual Cost** |
|------------|---------------------|-----------------|-----------------|
| ₹10,000 | 2.36% | **₹236** | **₹2,832** |
| ₹50,000 | 2.36% | **₹1,180** | **₹14,160** |
| ₹1,00,000 | 2.36% | **₹2,360** | **₹28,320** |
| ₹5,00,000 | 2.36% | **₹11,800** | **₹1,41,600** |
| ₹10,00,000 | 2.36% | **₹23,600** | **₹2,83,200** |

**Hard limits:**  
- Single transaction max: ₹5,00,000 (standard); higher on request  
- Payout limit: ₹2,00,000/day per bank account (default)  
- International cards: 3% fee instead of 2%  
**Tip:** Negotiate custom rates (< 2%) once GMV crosses ₹5 lakh/month.

---

## 6. Backend Hosting (Django API — recommended options)

> Not in the credential list but required to go live.

| Provider | Tier | RAM / CPU | **Monthly** | **Annual** | Best for |
|----------|------|-----------|------------|-----------|---------|
| **Railway** | Hobby | Auto-scale | **$5** | **$60** | Quick launch |
| **DigitalOcean** | Droplet Basic | 1 GB / 1 vCPU | **$6** | **$72** | Budget |
| **DigitalOcean** | Droplet General | 2 GB / 1 vCPU | **$12** | **$144** | Recommended start |
| **AWS EC2** | t3.small | 2 GB / 2 vCPU | **~$15** | **~$180** | AWS ecosystem |
| **AWS EC2** | t3.medium | 4 GB / 2 vCPU | **~$30** | **~$360** | Medium traffic |
| **Render** | Starter | 512 MB | **$7** | **$84** | Easy deploy |

**Add-ons (AWS):**  
- RDS PostgreSQL (db.t3.micro): ~$15/month  
- ElastiCache Redis (cache.t3.micro): ~$13/month  

---

## Total Monthly & Annual Cost Summary

### Scenario A — Pre-launch / Beta (< 500 users)

| Service | Monthly | Annual |
|---------|---------|--------|
| Firebase | $0 | $0 |
| Google Maps | $0 | $0 |
| Twilio (500 OTPs) | $5.40 | $64.80 |
| AWS S3 (5 GB) | $2.00 | $24.00 |
| Razorpay (₹10K GMV) | ₹236 (~$2.84) | ₹2,832 (~$34) |
| Backend hosting | $12.00 | $144.00 |
| **TOTAL** | **~$22 / ₹1,826** | **~$267 / ₹22,161** |

### Scenario B — Growth (1,000–5,000 active users)

| Service | Monthly | Annual |
|---------|---------|--------|
| Firebase | $0 | $0 |
| Google Maps | $0 (within credit) | $0 |
| Twilio (5,000 OTPs) | $43.65 | $523.80 |
| AWS S3 (20 GB + 50 GB transfer) | $5.00 | $60.00 |
| Razorpay (₹1 lakh GMV) | ₹2,360 (~$28.43) | ₹28,320 (~$341) |
| Backend hosting (2 GB droplet) | $12.00 | $144.00 |
| **TOTAL** | **~$89 / ₹7,387** | **~$1,069 / ₹88,727** |

### Scenario C — Scale (10,000–50,000 active users)

| Service | Monthly | Annual |
|---------|---------|--------|
| Firebase | $0 | $0 |
| Google Maps | ~$50 (beyond credit) | ~$600 |
| Twilio (20,000 OTPs) | $172.15 | $2,065.80 |
| AWS S3 (100 GB + 300 GB transfer) | $30.00 | $360.00 |
| Razorpay (₹5 lakh GMV) | ₹11,800 (~$142) | ₹1,41,600 (~$1,706) |
| Backend hosting (EC2 t3.medium + RDS) | $45.00 | $540.00 |
| **TOTAL** | **~$439 / ₹36,437** | **~$5,272 / ₹4,37,576** |

---

## One-Time Setup Costs

| Item | Estimated Cost |
|------|---------------|
| India DLT Registration (Twilio/TRAI) | ₹10,000–₹25,000 |
| Domain (nearkart.in, 1 year) | ₹800–₹1,500 |
| SSL Certificate (Let's Encrypt) | **Free** |
| Google Play Store developer account | $25 (one-time) |
| Apple App Store (if iOS added) | $99/year |
| Release keystore signing | Free |

---

## Key Limits at a Glance

| Service | Critical Limit | Action if hit |
|---------|---------------|---------------|
| Firebase FCM | None | No action needed |
| Google Maps | $200/month free credit | Add billing method; cost kicks in beyond |
| Twilio SMS | 1 SMS/sec default | Request throughput increase |
| Twilio OTP | Account spending limit (set by you) | Raise limit in console |
| AWS S3 | 5 TB per object, no bucket size limit | Lifecycle rules to reduce cost |
| Razorpay | ₹5 lakh / single transaction | Contact support for higher limit |
| Razorpay | ₹2 lakh/day payout | Contact support for higher payout |

---

*Generated for NearKart v1.0 — update this file when service tiers or volumes change.*
