# Sprint 26 — Backend Testing Checklist: Product ID System

---

## Setup

- `docker compose up -d` — Django restarted after services.py + views.py changes
- Vendor test account active

---

## Part A — Code Format

- [ ] `GET /products/vendor/generate-code/?category=electronics` → returns `NS-VE-BAN-ELEC-{5chars}`
- [ ] `?category=fashion` → `FASH` segment
- [ ] `?category=jewellery` → `JEWE` segment
- [ ] `?category=footwear` → `FOOT` segment
- [ ] `?category=decor` → `DECO` segment
- [ ] `?category=furniture` → `FURN` segment
- [ ] `?category=gifts` → `GIFT` segment
- [ ] `?category=beauty` → `BEAU` segment
- [ ] `?category=food` → `FOOD` segment
- [ ] `?category=unknown` → `GEN` segment (fallback)
- [ ] No category param → fallback prefix, no crash

---

## Part B — Store Abbreviation

- [ ] "Sneha's Fashion House" → `SFH`
- [ ] "Vikram Electronics" → `VE`
- [ ] Two stores with same raw initials → second gets number suffix (`VE2`)
- [ ] Store name with special chars (apostrophes, numbers) → stripped correctly before abbreviation

---

## Part C — Locality Code

- [ ] Store with locality "Banjara Hills" → `BAN`
- [ ] Store with locality "Koramangala" → `KOR`
- [ ] Store with empty locality but valid address → falls back to address first 3 chars
- [ ] Store with no locality and no address → `GEN`

---

## Part D — Auto-Assignment on Product Create

- [ ] `POST /products/` without `product_code` → response includes structured `NS-` code
- [ ] Code matches store's abbreviation + locality + requested category
- [ ] `POST /products/` with explicit `product_code` → custom code used, not overwritten

---

## Part E — Collision Safety

- [ ] Same endpoint called 10 times → all codes have different Unique suffix
- [ ] No `IntegrityError` on bulk creation (collision retry loop works)

---

## Part F — Existing Products Untouched

- [ ] `Product.objects.filter(product_code__startswith='NKP').count()` → same as before sprint
- [ ] Existing product detail API returns old `NKP-` code unchanged
- [ ] No migration ran, no data modified

---

## Django Shell Verification

```python
# docker compose exec django python manage.py shell

from apps.products.services import ProductService
from apps.stores.models import Store

# Test code generation for a real store
store = Store.objects.filter(phone__startswith='+919000000004').first()
print(ProductService._generate_product_code(store=store, category='fashion'))
# Expected: NS-SFH-BAN-FASH-XXXXX (or similar)

# Verify old codes untouched
from apps.products.models import Product
print(Product.objects.filter(product_code__startswith='NKP').count())
print(Product.objects.filter(product_code__startswith='NS').count())
```
