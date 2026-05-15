# Sprint 3 — Store + Product Module

**Goal:** Vendors create stores and products. Customers discover nearby stores.
**Status:** Not started
**Time estimate:** ~20 hours
**Depends on:** Sprint 2 (Auth) must be complete

---

## What Will Be Built

- Store model (location, category, hours, reviews, follow)
- Product model (variants, images, wishlist)
- Geo search — find stores/products within radius
- Redis caching for nearby queries
- QR code generation per store

## Endpoints to Build

```
GET  /api/v1/stores/nearby/       Find stores near me
GET  /api/v1/stores/:id/          Store detail
POST /api/v1/stores/              Create store (vendor only)
PUT  /api/v1/stores/:id/          Update store
POST /api/v1/stores/:id/follow/   Follow a store

GET  /api/v1/products/nearby/     Find products near me
GET  /api/v1/products/search/     Search products by name
GET  /api/v1/products/:id/        Product detail
POST /api/v1/products/            Create product (vendor only)
POST /api/v1/products/:id/wishlist/ Add to wishlist
```

*Docs and testing checklist will be added when this sprint starts.*
