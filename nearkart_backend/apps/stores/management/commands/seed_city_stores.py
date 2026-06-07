"""
Management command: seed_city_stores
Creates stores across 5 cities (Hyderabad, Bangalore, Chennai, Yanam, Peapully)
using NearSpot Excel area data.

Usage:
    python manage.py seed_city_stores
    python manage.py seed_city_stores --excel /path/to/NearSpot_5_Cities_Areas_Updated.xlsx
    python manage.py seed_city_stores --clear
"""
import os
import uuid
import random
from datetime import time

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.contrib.auth.hashers import make_password


# ── Constants ──────────────────────────────────────────────────────────────────

STORES_PER_AREA = 20
COORD_SCATTER   = 0.0015   # ~150 metres in degrees
BATCH_SIZE      = 500

CATEGORIES = [
    'fashion', 'jewellery', 'footwear', 'decor',
    'furniture', 'gifts', 'beauty', 'food', 'electronics',
]

STORE_NAME_SUFFIXES = {
    'fashion':     ['Fashion Hub', 'Boutique', 'Ethnic Wear', 'Dress Studio', 'Saree Center', 'Collections'],
    'jewellery':   ['Jewels', 'Gold Palace', 'Jewellery Hub', 'Ornaments Store', 'Diamond House'],
    'footwear':    ['Footwear', 'Shoe Mart', 'Step In', 'Walk Easy', 'Foot Comfort'],
    'decor':       ['Decor Studio', 'Home Decor', 'Interior Hub', 'Art & Craft', 'Decor Palace'],
    'furniture':   ['Furniture World', 'Wood Works', 'Home Furnish', 'Furniture Hub', 'Comfort Living'],
    'gifts':       ['Gift Shop', 'Gift Gallery', 'Occasions', 'Gift World', 'Surprise Store'],
    'beauty':      ['Beauty Salon', 'Cosmetics Hub', 'Glow Studio', 'Beauty Palace', 'Skin Care'],
    'food':        ['Restaurant', 'Food Corner', 'Cafe', 'Eatery', 'Tiffin Center', 'Dhaba'],
    'electronics': ['Electronics', 'Mobile Hub', 'Gadget Store', 'Tech World', 'Digital Hub'],
}

CATEGORY_DESCRIPTIONS = {
    'fashion':     'Trendy ethnic and western wear — kurtas, sarees, lehengas and more.',
    'jewellery':   'Handcrafted gold, silver, and temple jewellery for every occasion.',
    'footwear':    'Comfortable and stylish footwear — formal, casual and sports.',
    'decor':       'Unique handmade décor to transform your living space.',
    'furniture':   'Quality furniture for every room — modern and traditional styles.',
    'gifts':       'Thoughtful gifts for every occasion — birthdays, weddings and more.',
    'beauty':      'Premium beauty and skincare products for a glowing look.',
    'food':        'Delicious home-style food and snacks made fresh daily.',
    'electronics': 'Latest gadgets, mobiles, and electronics at the best prices.',
}

# Curated Unsplash photo IDs — category-relevant, stable URLs
CATEGORY_IMAGES = {
    'fashion': {
        'logos': [
            'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1594938298603-c8148c4b58f8?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1559526324-593bc073d938?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1571513722275-4b41940f54b8?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1594938298603-c8148c4b58f8?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1559526324-593bc073d938?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1571513722275-4b41940f54b8?w=800&h=300&fit=crop',
        ],
    },
    'jewellery': {
        'logos': [
            'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=800&h=300&fit=crop',
        ],
    },
    'footwear': {
        'logos': [
            'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=800&h=300&fit=crop',
        ],
    },
    'decor': {
        'logos': [
            'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1565183928294-7063f23ce0f8?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1567016432779-094069958ea5?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1565183928294-7063f23ce0f8?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1567016432779-094069958ea5?w=800&h=300&fit=crop',
        ],
    },
    'furniture': {
        'logos': [
            'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=800&h=300&fit=crop',
        ],
    },
    'gifts': {
        'logos': [
            'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1512909006721-3d6018887383?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1512909006721-3d6018887383?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800&h=300&fit=crop',
        ],
    },
    'beauty': {
        'logos': [
            'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=800&h=300&fit=crop',
        ],
    },
    'food': {
        'logos': [
            'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&h=300&fit=crop',
        ],
    },
    'electronics': {
        'logos': [
            'https://images.unsplash.com/photo-1518770660439-4636190af475?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=200&h=200&fit=crop',
            'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=200&h=200&fit=crop',
        ],
        'banners': [
            'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800&h=300&fit=crop',
            'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=800&h=300&fit=crop',
        ],
    },
}

CITY_ADMINS = [
    {'city': 'Hyderabad', 'phone': '+916000000001', 'name': 'Hyderabad City Admin'},
    {'city': 'Bangalore', 'phone': '+916000000002', 'name': 'Bangalore City Admin'},
    {'city': 'Chennai',   'phone': '+916000000003', 'name': 'Chennai City Admin'},
    {'city': 'Yanam',     'phone': '+916000000004', 'name': 'Yanam City Admin'},
    {'city': 'Peapully',  'phone': '+916000000005', 'name': 'Peapully City Admin'},
]


def _unique_profile_id(prefix='V'):
    return f'{prefix}{uuid.uuid4().hex[:7].upper()}'


def _bulk_insert(manager, objects, batch_size=BATCH_SIZE, ignore_conflicts=False):
    created = []
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        result = manager.bulk_create(batch, ignore_conflicts=ignore_conflicts)
        created.extend(result)
    return created


class Command(BaseCommand):
    help = 'Seed stores across 5 cities from NearSpot Excel area data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel',
            default=os.path.expanduser('~/Downloads/NearSpot_5_Cities_Areas_Updated.xlsx'),
            help='Path to the Excel file (default: ~/Downloads/NearSpot_5_Cities_Areas_Updated.xlsx)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all previously seeded city stores and admin users before re-seeding',
        )

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError:
            self.stderr.write(self.style.ERROR('openpyxl not installed. Run: pip install openpyxl'))
            return

        from apps.auth_app.models import User
        from apps.stores.models import Store, StoreHours

        excel_path = options['excel']
        if not os.path.exists(excel_path):
            self.stderr.write(self.style.ERROR(f'Excel file not found: {excel_path}'))
            self.stderr.write('Pass the correct path with --excel /path/to/file.xlsx')
            return

        # ── Clear ─────────────────────────────────────────────────────────────
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing previously seeded data...'))
            admin_phones = [a['phone'] for a in CITY_ADMINS]
            User.objects.filter(phone_number__in=admin_phones).delete()
            deleted = User.objects.filter(phone_number__startswith='+917').delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted[0]} records.'))

        # ── Step 1: Read Excel ────────────────────────────────────────────────
        self.stdout.write('\nReading Excel file...')
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        city_areas = {}
        for city in ['Hyderabad', 'Bangalore', 'Chennai', 'Yanam', 'Peapully']:
            ws = wb[city]
            areas = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 4:
                    continue
                lng, lat, _, name = row[0], row[1], row[2], row[3]
                if name and lat is not None and lng is not None:
                    areas.append({'name': str(name), 'lat': float(lat), 'lng': float(lng)})
            city_areas[city] = areas
            self.stdout.write(f'  {city}: {len(areas)} areas')

        total_areas  = sum(len(v) for v in city_areas.values())
        total_stores = total_areas * STORES_PER_AREA
        self.stdout.write(f'\nTotal: {total_areas} areas → {total_stores} stores to create\n')

        # ── Step 2: City admin users ──────────────────────────────────────────
        self.stdout.write('Creating city admin users...')
        for admin in CITY_ADMINS:
            _, created = User.objects.get_or_create(
                phone_number=admin['phone'],
                defaults={
                    'role':                'admin',
                    'full_name':           admin['name'],
                    'admin_assigned_city': admin['city'],
                    'is_staff':            True,
                    'is_active':           True,
                    'profile_id':          _unique_profile_id('ADM'),
                    'password':            make_password(None),
                },
            )
            status = 'created' if created else 'already exists'
            self.stdout.write(f'  {admin["name"]} ({admin["city"]}) — {status}')

        # ── Step 3: Vendor users + stores + hours per city ────────────────────
        vendor_counter = 1
        grand_total    = 0

        for city, areas in city_areas.items():
            self.stdout.write(f'\n{city} — {len(areas)} areas × {STORES_PER_AREA} stores...')

            # Build flat list of all store data for this city
            store_specs = []
            for area in areas:
                for i in range(STORES_PER_AREA):
                    category = CATEGORIES[i % len(CATEGORIES)]
                    suffix   = random.choice(STORE_NAME_SUFFIXES[category])
                    name     = f'{area["name"]} {suffix}'
                    lat      = area['lat'] + random.uniform(-COORD_SCATTER, COORD_SCATTER)
                    lng      = area['lng'] + random.uniform(-COORD_SCATTER, COORD_SCATTER)
                    phone    = f'+917{str(vendor_counter).zfill(9)}'
                    vendor_counter += 1

                    store_specs.append({
                        'name':     name,
                        'category': category,
                        'area':     area['name'],
                        'city':     city,
                        'lat':      lat,
                        'lng':      lng,
                        'phone':    phone,
                    })

            # Bulk create vendor users
            user_objects = [
                User(
                    phone_number=s['phone'],
                    role='vendor',
                    full_name=f'{s["name"]} Owner',
                    profile_id=_unique_profile_id('V'),
                    password=make_password(None),
                    is_active=True,
                )
                for s in store_specs
            ]
            _bulk_insert(User.objects, user_objects, ignore_conflicts=True)

            # Fetch back by phone to get DB IDs
            phones   = [s['phone'] for s in store_specs]
            user_map = {
                u.phone_number: u
                for u in User.objects.filter(phone_number__in=phones)
            }

            # Build store objects
            store_objects = []
            for s in store_specs:
                user = user_map.get(s['phone'])
                if not user:
                    continue
                logo   = random.choice(CATEGORY_IMAGES[s['category']]['logos'])
                banner = random.choice(CATEGORY_IMAGES[s['category']]['banners'])
                store_objects.append(Store(
                    owner=user,
                    name=s['name'],
                    description=CATEGORY_DESCRIPTIONS[s['category']],
                    category=s['category'],
                    phone=s['phone'],
                    address=f'Shop, {s["area"]}, {s["city"]}',
                    locality=s['area'],
                    location=Point(s['lng'], s['lat'], srid=4326),
                    logo_url=logo,
                    banner_url=banner,
                    is_active=True,
                    is_verified=random.random() < 0.8,   # 80% verified
                    is_open=random.random() < 0.7,       # 70% open
                    performance_score=round(random.uniform(0.0, 5.0), 1),
                ))

            created_stores = _bulk_insert(Store.objects, store_objects)

            # Bulk create store hours (Mon–Sat open, Sunday closed)
            hours_objects = [
                StoreHours(
                    store=store,
                    day=day,
                    open_time=time(10, 0),
                    close_time=time(21, 0),
                    is_closed=(day == 6),
                )
                for store in created_stores
                for day in range(7)
            ]
            _bulk_insert(StoreHours.objects, hours_objects, batch_size=1000)

            grand_total += len(created_stores)
            self.stdout.write(self.style.SUCCESS(
                f'  ✅  {city}: {len(created_stores)} stores, {len(hours_objects)} store-hours rows'
            ))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f'\n✅  Done!'))
        self.stdout.write(f'   Stores created  : {grand_total}')
        self.stdout.write(f'   City admins     : {len(CITY_ADMINS)}  (phones +916000000001 – +916000000005)')
        self.stdout.write(f'   Vendor users    : {vendor_counter - 1}  (phones +9170000000001 onwards)')
        self.stdout.write(f'   Store hours rows: {grand_total * 7}')
        self.stdout.write('\n   To reset and re-seed: python manage.py seed_city_stores --clear')
