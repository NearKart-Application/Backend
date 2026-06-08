# Sprint 26 — Structured Product ID System (Backend)

**Branch:** `MAP-Integration`
**Date:** June 2026
**Status:** Complete

---

## Overview

Product codes are now structured: `NS-{ShopAbbr}-{LocalityCode}-{CategoryCode}-{Unique}`

All logic lives in `apps/products/services.py`. No model changes. No migration. Existing `NKP-` codes are untouched.

---

## Changes

### `apps/products/services.py`

**Added `_CATEGORY_CODES` dict:**
```python
_CATEGORY_CODES = {
    'fashion':     'FASH',
    'jewellery':   'JEWE',
    'footwear':    'FOOT',
    'decor':       'DECO',
    'furniture':   'FURN',
    'gifts':       'GIFT',
    'beauty':      'BEAU',
    'food':        'FOOD',
    'electronics': 'ELEC',
}
```

**Added `_store_abbreviation(store) -> str`:**
```python
def _store_abbreviation(store) -> str:
    import re
    from apps.stores.models import Store
    words = re.sub(r'[^a-zA-Z\s]', '', store.name.strip()).split()
    raw = ''.join(w[0].upper() for w in words if w) or 'NS'
    # Count stores with same raw initials created before this one → clash-safe
    rank = 0
    for s in Store.objects.filter(created_at__lt=store.created_at).order_by('created_at').only('name'):
        s_words = re.sub(r'[^a-zA-Z\s]', '', s.name.strip()).split()
        if ''.join(w[0].upper() for w in s_words if w) == raw:
            rank += 1
    return raw if rank == 0 else f'{raw}{rank + 1}'
```

**Added `_locality_code(store) -> str`:**
```python
def _locality_code(store) -> str:
    import re
    src = store.locality or store.address or ''
    alpha = re.sub(r'[^a-zA-Z]', '', src)
    return alpha[:3].upper() if alpha else 'GEN'
```

**Updated `ProductService._generate_product_code(store=None, category='')`:**
```python
@staticmethod
def _generate_product_code(store=None, category: str = '') -> str:
    import random, string
    from .models import Product

    if store is not None:
        shop_abbr = _store_abbreviation(store)
        loc_code  = _locality_code(store)
        cat_code  = _CATEGORY_CODES.get(category.lower().strip(), 'GEN')
        prefix    = f'NS-{shop_abbr}-{loc_code}-{cat_code}'
    else:
        prefix = 'NS'

    for _ in range(10):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        code = f'{prefix}-{suffix}'
        if not Product.objects.filter(product_code=code).exists():
            return code
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f'{prefix}-{suffix}'
```

**Updated `ProductService.create()` to pass store + category:**
```python
validated_data.setdefault(
    'product_code',
    ProductService._generate_product_code(
        store=store,
        category=validated_data.get('category', ''),
    )
)
```

### `apps/products/views.py`

**Updated `GenerateProductCodeView.get()`:**
```python
def get(self, request):
    category = request.query_params.get('category', '')
    store = getattr(request.user, 'store', None)
    code = ProductService._generate_product_code(store=store, category=category)
    return Response({'product_code': code})
```

---

## API Endpoint

```
GET /api/v1/products/vendor/generate-code/?category=electronics
Authorization: Bearer {{vendor_token}}
```

Response:
```json
{ "product_code": "NS-VE-BAN-ELEC-X7K2P" }
```

---

## No Migration Required

- `product_code` column already exists on `Product` model
- Old `NKP-` codes remain valid — no data touched
- New code format is collision-checked against existing codes (both `NS-` and `NKP-` formats coexist safely)

---

## Files Changed

| File | Change |
|------|--------|
| `apps/products/services.py` | `_CATEGORY_CODES`, `_store_abbreviation()`, `_locality_code()`, updated `_generate_product_code()` and `create()` |
| `apps/products/views.py` | `GenerateProductCodeView` passes `store` + `category` to `_generate_product_code()` |
