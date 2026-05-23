"""
Management command: seed_dev_users

Creates all dev test users from the DevTestUsers list (matching the mobile app),
gives each vendor their own store with products, and gives each customer:
  - registered_location set to Kukatpally
  - follows all 4 dev vendor stores
  - 2 reservations (1 pending/active, 1 completed)
  - 1 conversation per vendor with realistic messages
  - 4 notifications (reservation, store_opened, new_offer, new_message)

Run:
    python manage.py seed_dev_users
    python manage.py seed_dev_users --clear   (wipes and re-seeds dev users only)

All phone numbers and OTPs match DevTestUsers.kt in the mobile app.
The backend OTP check is bypassed for these users by the mobile devBypassLogin().
DO NOT DELETE this command or any user entries — they map to real devices/testers.
"""
from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


# Different public HLS test streams so each vendor's videos play distinct content
DEV_HLS_POOL = [
    'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8',
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/img_bipbop_adv_example_ts/master.m3u8',
    'https://test-streams.mux.dev/pts_shift/master.m3u8',
    'https://playertest.longtailvideo.com/adaptive/bipbop/gear4/prog_index.m3u8',
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/adv_dv_atmos/main.m3u8',
    'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',  # cycle back
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8',
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_16x9/bipbop_16x9_variant.m3u8',
]


# ── User definitions — KEEP IN SYNC with DevTestUsers.kt ─────────────────────
DEV_USERS = [
    # (phone, full_name, role)
    ('+919000000001', 'Arjun Kumar',  'customer'),
    ('+919000000002', 'Priya Sharma', 'customer'),
    ('+919000000003', 'Rahul Verma',  'customer'),
    ('+919000000006', 'Meena Patel',  'customer'),
    ('+919000000009', 'Sanjay Rao',   'customer'),
    ('+919000000010', 'Lakshmi Nair', 'customer'),
    ('+919000000004', 'Sneha Reddy',  'vendor'),
    ('+919000000005', 'Vikram Iyer',  'vendor'),
    ('+919000000007', 'Kiran Naidu',  'vendor'),
    ('+919000000008', 'Divya Mehta',  'vendor'),
    ('+919999999999', 'Dev Vendor',   'vendor'),
    ('+918888888888', 'Dev Customer', 'customer'),
]

# ── Vendor stores — one per dev vendor ───────────────────────────────────────
# Each store is within 2 km of Kukatpally (17.4948, 78.3996) so it shows up
# in the nearby feed for customers whose location is set to Kukatpally.

DEV_VENDOR_STORES = {
    '+919000000004': {
        'name': "Sneha's Fashion House",
        'category': 'fashion',
        'description': 'Trendy kurtas, suits, and ethnic wear for the modern woman.',
        'address': 'Plot 3, KPHB Phase 2, Kukatpally, Hyderabad',
        'locality': 'Kukatpally',
        'lat': 17.4952, 'lng': 78.3988,
        'logo':   'https://picsum.photos/seed/dev-sneha-logo/200/200',
        'banner': 'https://picsum.photos/seed/dev-sneha-banner/800/300',
        'offer': ('Festival Sale — 20% Off', 'Get 20% off on all ethnic wear this season.', 20),
        'videos': [
            ('New Collection Arrived! 🎉', 'Check out our latest ethnic wear collection — kurtas, suits, and more.',
             'https://picsum.photos/seed/dev-sneha-v1/400/700', 45, 120, 18),
            ('Festival Sale Preview 🛍️', '20% off on all ethnic wear. Come visit us at KPHB Phase 2!',
             'https://picsum.photos/seed/dev-sneha-v2/400/700', 32, 87, 12),
        ],
        'products': [
            # (name, category, subcategory, base_price, sale_price, sizes)
            ('Blue Embroidered Kurta',  'clothing', 'kurta',   750,  None, ['S', 'M', 'L', 'XL']),
            ('Green Palazzo Set',       'clothing', 'palazzo', 1100, None, ['S', 'M', 'L', 'XL']),
            ('Red Anarkali Suit',       'clothing', 'suit',    1499, 1199, ['S', 'M', 'L']),
            ('Yellow Floral Dupatta',   'clothing', 'dupatta', 299,  None, ['Free Size']),
            ('Purple Crop Top',         'clothing', 'top',     449,  None, ['XS', 'S', 'M']),
            ('Orange Wrap Dress',       'clothing', 'dress',   899,  749,  ['S', 'M', 'L']),
        ],
    },
    '+919000000005': {
        'name': 'Vikram Electronics',
        'category': 'electronics',
        'description': 'Genuine accessories for phones, laptops, and audio — all at fair prices.',
        'address': 'Shop 9, KPHB Colony, Hyderabad',
        'locality': 'KPHB',
        'lat': 17.4965, 'lng': 78.3951,
        'logo':   'https://picsum.photos/seed/dev-vikram-logo/200/200',
        'banner': 'https://picsum.photos/seed/dev-vikram-banner/800/300',
        'offer': ('Weekend Deal — Flat ₹100 Off', 'Flat ₹100 off on all accessories above ₹499.', None),
        'videos': [
            ('Best Wireless Earphones Under ₹900 🎧', 'Crystal clear sound, 30-hour battery — now at Vikram Electronics.',
             'https://picsum.photos/seed/dev-vikram-v1/400/700', 38, 203, 31),
            ('Power Bank Review — Worth It? ⚡', 'Portable 10000mAh power bank — honest review from our store.',
             'https://picsum.photos/seed/dev-vikram-v2/400/700', 55, 156, 24),
        ],
        'products': [
            ('Wireless Earphones',     'electronics', 'audio',       899,  749,  []),
            ('USB-C Fast Charger',     'electronics', 'chargers',    349,  None, []),
            ('Tempered Glass Pack',    'electronics', 'accessories', 149,  None, []),
            ('Portable Power Bank',    'electronics', 'power',       1299, 999,  []),
            ('Laptop Stand Foldable',  'electronics', 'accessories', 799,  None, []),
            ('Braided USB Cable 2m',   'electronics', 'cables',      199,  None, []),
        ],
    },
    '+919000000007': {
        'name': 'Kiran Footwear Zone',
        'category': 'footwear',
        'description': 'Comfortable and stylish footwear for every occasion.',
        'address': '12, Bachupally Main Road, Hyderabad',
        'locality': 'Bachupally',
        'lat': 17.5005, 'lng': 78.3982,
        'logo':   'https://picsum.photos/seed/dev-kiran-logo/200/200',
        'banner': 'https://picsum.photos/seed/dev-kiran-banner/800/300',
        'offer': ('Buy 2 Get 10% Off', 'Buy any 2 footwear and get 10% off the second pair.', 10),
        'videos': [
            ('White Sneakers — Try On 👟', 'Our most popular white canvas sneakers. See how they look!',
             'https://picsum.photos/seed/dev-kiran-v1/400/700', 29, 94, 11),
            ('New Arrivals This Week 👠', 'Block heels, kolhapuri chappals and formals — just arrived.',
             'https://picsum.photos/seed/dev-kiran-v2/400/700', 41, 67, 8),
        ],
        'products': [
            ('White Canvas Sneakers',   'footwear', 'sneakers', 699,  549,  ['6', '7', '8', '9', '10']),
            ('Brown Leather Sandals',   'footwear', 'sandals',  849,  None, ['5', '6', '7', '8']),
            ('Black Formal Shoes',      'footwear', 'formals',  1299, 999,  ['6', '7', '8', '9']),
            ('Pink Block Heels',        'footwear', 'heels',    799,  None, ['5', '6', '7', '8']),
            ('Blue Sports Shoes',       'footwear', 'sports',   1499, None, ['6', '7', '8', '9', '10']),
            ('Tan Kolhapuri Chappals',  'footwear', 'chappals', 449,  None, ['5', '6', '7', '8']),
        ],
    },
    '+919000000008': {
        'name': "Divya's Jewellery Corner",
        'category': 'jewellery',
        'description': 'Handcrafted gold, silver, and imitation jewellery for every occasion.',
        'address': 'Shop 7, Miyapur Road, Hyderabad',
        'locality': 'Miyapur',
        'lat': 17.4902, 'lng': 78.4015,
        'logo':   'https://picsum.photos/seed/dev-divya-logo/200/200',
        'banner': 'https://picsum.photos/seed/dev-divya-banner/800/300',
        'offer': ('Festive Collection Live', 'New festive jewellery collection now available in store!', None),
        'videos': [
            ('Festive Jewellery Collection 💍', 'Gold jhumkas, pearl necklaces and kundan sets — perfect for every occasion.',
             'https://picsum.photos/seed/dev-divya-v1/400/700', 52, 178, 27),
            ('Silver Bangles — Unboxing ✨', 'Beautiful 925 silver bangle set at just ₹399. Limited stock!',
             'https://picsum.photos/seed/dev-divya-v2/400/700', 35, 112, 19),
        ],
        'products': [
            ('Gold Jhumka Earrings',   'jewellery', 'earrings',  1199, None, []),
            ('Silver Bangle Set',      'jewellery', 'bangles',   499,  399,  []),
            ('Pearl Necklace',         'jewellery', 'necklace',  2499, None, []),
            ('Kundan Bangles Set',     'jewellery', 'bangles',   899,  None, []),
            ('Rose Gold Ring',         'jewellery', 'rings',     699,  599,  ['6', '7', '8']),
            ('Temple Necklace Set',    'jewellery', 'necklace',  1799, None, []),
        ],
    },
    '+919999999999': {
        'name': 'NearKart Demo Hub',
        'category': 'fashion',
        'description': 'Your go-to store for trendy kurtas, fusion wear, and everyday fashion — all under one roof in Kukatpally.',
        'address': 'Plot 14, KPHB Phase 3, Kukatpally, Hyderabad',
        'locality': 'Kukatpally',
        'lat': 17.4950, 'lng': 78.3994,
        'logo':   'https://picsum.photos/seed/dev-hub-logo/200/200',
        'banner': 'https://picsum.photos/seed/dev-hub-banner/800/300',
        'offer': ('Summer Sale — Flat 25% Off', 'Get 25% off on all kurtas and fusion wear this summer.', 25),
        'videos': [
            ('Summer Collection 2026 ☀️', 'Our hottest picks for summer — breezy kurtas, palazzo sets, and fusion tops.',
             'https://picsum.photos/seed/dev-hub-v1/400/700', 48, 312, 41),
            ('New Arrivals This Week 🛍️', 'Fresh stock just arrived — floral prints, crop tops, and embroidered dupattas.',
             'https://picsum.photos/seed/dev-hub-v2/400/700', 36, 198, 27),
            ('Customer Favourites 💛', 'Top 5 bestselling products from our store — see what everyone is loving!',
             'https://picsum.photos/seed/dev-hub-v3/400/700', 55, 427, 63),
        ],
        'products': [
            ('Floral Print Kurta',        'clothing', 'kurta',   699,  549,  ['XS', 'S', 'M', 'L', 'XL']),
            ('Embroidered Palazzo Set',   'clothing', 'palazzo', 1299, 999,  ['S', 'M', 'L', 'XL']),
            ('Crop Top & Skirt Set',      'clothing', 'co-ord',  1099, None, ['XS', 'S', 'M', 'L']),
            ('Printed Fusion Tunic',      'clothing', 'tunic',   849,  699,  ['S', 'M', 'L', 'XL', 'XXL']),
            ('Cotton Everyday Kurti',     'clothing', 'kurti',   449,  None, ['XS', 'S', 'M', 'L', 'XL']),
            ('Georgette Dupatta',         'clothing', 'dupatta', 349,  None, ['Free Size']),
            ('Linen Straight Pants',      'clothing', 'pants',   799,  649,  ['26', '28', '30', '32', '34']),
            ('Embroidered Jacket Kurti',  'clothing', 'kurti',   1499, 1199, ['S', 'M', 'L', 'XL']),
        ],
    },
}

# ── Conversations — per customer, rotating over vendor stores ─────────────────
# Each sub-list is (customer_msg, vendor_msg) pairs for that vendor.
# Indexed as: CHAT_SCRIPTS[vendor_idx % len][customer_name_prefix]
# Simplified: 4 script variants rotate across customers.

CHAT_SCRIPTS = {
    'fashion': [
        ('Hi! Do you have this kurta in size M?',             'customer'),
        ('Yes, the Blue Embroidered Kurta is available in M!', 'vendor'),
        ('What is the fabric?',                                'customer'),
        ('It is 100% cotton — very comfortable for daily wear.', 'vendor'),
        ('Can I reserve it?',                                  'customer'),
        ('Sure! I have created a reservation for you.',        'vendor'),
    ],
    'electronics': [
        ('Are the wireless earphones compatible with Android?', 'customer'),
        ('Yes, they work with all Bluetooth 5.0 devices.',     'vendor'),
        ('What is the battery life?',                          'customer'),
        ('Up to 30 hours with the charging case.',             'vendor'),
        ('I will come by to check them out.',                  'customer'),
        ('We are open till 9 PM. See you!',                    'vendor'),
    ],
    'footwear': [
        ('Do you have white sneakers in size 8?',              'customer'),
        ('Yes! The White Canvas Sneakers are in stock for 8.', 'vendor'),
        ('Are they good for daily walking?',                   'customer'),
        ('Absolutely — cushioned sole, very lightweight.',     'vendor'),
        ('I will reserve them.',                               'customer'),
        ('Done! Reservation confirmed. Pick up by 9 PM.',      'vendor'),
    ],
    'jewellery': [
        ('Do you have gold jhumka earrings?',                       'customer'),
        ('Yes, we have beautiful 22k gold-plated jhumkas at ₹1,199.', 'vendor'),
        ('Are they hallmarked?',                                    'customer'),
        ('Yes, all gold jewellery is BIS hallmarked.',              'vendor'),
        ('I will visit the store tomorrow.',                        'customer'),
        ('We are open 10 AM to 9 PM. Looking forward to your visit!', 'vendor'),
    ],
}

# ── Reservation rotation: (vendor_phone, product_index, status) per customer ──
# Each customer gets 2 reservations from 2 different stores.
RESERVATION_ROTATION = [
    # (pending_vendor_phone, prod_idx, completed_vendor_phone, prod_idx)
    ('+919000000004', 0, '+919000000005', 0),  # Arjun:  Sneha pending, Vikram completed
    ('+919000000007', 0, '+919000000008', 0),  # Priya:  Kiran pending, Divya completed
    ('+919000000005', 1, '+919000000007', 1),  # Rahul:  Vikram pending, Kiran completed
    ('+919000000008', 1, '+919000000004', 1),  # Meena:  Divya pending, Sneha completed
    ('+919000000004', 2, '+919000000007', 2),  # Sanjay: Sneha pending, Kiran completed
    ('+919000000007', 0, '+919000000005', 1),  # Lakshmi: Kiran pending, Vikram completed
    ('+919000000004', 0, '+919000000008', 1),  # Dev Customer
]


class Command(BaseCommand):
    help = 'Seed all dev test users with stores, products, reservations, chats, and notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all dev users and their data before re-seeding',
        )

    def handle(self, *args, **options):
        from django.contrib.gis.geos import Point
        from apps.auth_app.models import User
        from apps.stores.models import Store, StoreHours, StoreFollow, StoreOffer
        from apps.products.models import Product, ProductVariant, ProductImage
        from apps.reservations.models import Reservation
        from apps.chat.models import Conversation, Message
        from apps.notifications.models import Notification
        from apps.videos.models import Video

        all_phones = [p for p, _, _ in DEV_USERS]

        # ── Clear if requested ────────────────────────────────────────────────
        if options['clear']:
            deleted, _ = User.objects.filter(phone_number__in=all_phones).delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted} dev user records (cascade).'))

        # ── 1. Create users ───────────────────────────────────────────────────
        # Must use create_user() (not get_or_create) so the custom UserManager
        # generates a unique profile_id — plain create() leaves it as '' which
        # hits the unique constraint if more than one user is created this way.
        kukatpally = Point(78.3996, 17.4948, srid=4326)  # (lng, lat)
        users = {}
        for phone, full_name, role in DEV_USERS:
            try:
                user = User.objects.get(phone_number=phone)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    phone_number=phone,
                    role=role,
                    full_name=full_name,
                )
                created = True
            user.full_name = full_name
            user.role = role
            user.registered_location = kukatpally
            user.save(update_fields=['full_name', 'role', 'registered_location'])
            users[phone] = user
            flag = '✅ created' if created else '   exists'
            self.stdout.write(f'  {flag}  {full_name} ({phone})')

        self.stdout.write('')

        # ── 2. Create vendor stores + products ────────────────────────────────
        stores = {}  # vendor_phone → Store
        global_video_idx = 0  # increments across all vendors so each video gets a distinct HLS URL
        for vendor_phone, store_data in DEV_VENDOR_STORES.items():
            vendor = users[vendor_phone]
            if hasattr(vendor, 'store'):
                store = vendor.store
                self.stdout.write(f'   exists  {store.name}')
            else:
                store = Store.objects.create(
                    owner=vendor,
                    name=store_data['name'],
                    description=store_data['description'],
                    category=store_data['category'],
                    phone=vendor_phone,
                    address=store_data['address'],
                    locality=store_data['locality'],
                    location=Point(store_data['lng'], store_data['lat'], srid=4326),
                    logo_url=store_data['logo'],
                    banner_url=store_data['banner'],
                    is_active=True,
                    is_verified=True,
                    is_open=True,
                )

                # Store hours: Mon–Sat 10:00–21:00, Sunday closed
                for day in range(7):
                    StoreHours.objects.create(
                        store=store,
                        day=day,
                        open_time=time(10, 0),
                        close_time=time(21, 0),
                        is_closed=(day == 6),
                    )

                # Active offer
                if store_data['offer']:
                    title, desc, pct = store_data['offer']
                    StoreOffer.objects.create(
                        store=store,
                        title=title,
                        description=desc,
                        discount_pct=pct,
                        valid_till=(timezone.now() + timedelta(days=30)).date(),
                        is_active=True,
                    )

                # Products
                for i, prod_data in enumerate(store_data['products']):
                    name, category, subcategory, base_price, sale_price, sizes = prod_data
                    seed = f'dev-{vendor_phone[-4:]}-p{i}'
                    product = Product.objects.create(
                        store=store,
                        name=name,
                        description=f'{name} — available at {store.name}, {store.locality}.',
                        category=category,
                        subcategory=subcategory,
                        status='active',
                        is_visible=True,
                        base_price=base_price,
                    )
                    ProductImage.objects.create(
                        product=product,
                        image_url=f'https://picsum.photos/seed/{seed}/400/500',
                        s3_key=f'dev/{seed}.jpg',
                        is_primary=True,
                        order=0,
                    )
                    ProductImage.objects.create(
                        product=product,
                        image_url=f'https://picsum.photos/seed/{seed}-b/400/500',
                        s3_key=f'dev/{seed}-b.jpg',
                        is_primary=False,
                        order=1,
                    )
                    variant_price = sale_price if sale_price else base_price
                    if sizes:
                        for j, size in enumerate(sizes):
                            stock = 5 if j == 0 else (3 if j == 1 else (1 if j < 4 else 0))
                            ProductVariant.objects.create(
                                product=product,
                                name=size,
                                sku=f'DEV-{str(product.id)[:8]}-{size}',
                                price=variant_price,
                                stock_quantity=stock,
                            )
                    else:
                        ProductVariant.objects.create(
                            product=product,
                            name='One Size',
                            sku=f'DEV-{str(product.id)[:8]}-OS',
                            price=variant_price,
                            stock_quantity=10,
                        )

                # Videos (2 per vendor store, status=ready so they appear in video feed)
                for v_idx, (title, desc, thumb, duration, views, likes) in enumerate(store_data.get('videos', [])):
                    hls_url = DEV_HLS_POOL[global_video_idx % len(DEV_HLS_POOL)]
                    global_video_idx += 1
                    Video.objects.get_or_create(
                        store=store,
                        title=title,
                        defaults=dict(
                            description=desc,
                            thumbnail_url=thumb,
                            video_url=hls_url,
                            status=Video.STATUS_READY,
                            duration_seconds=duration,
                            view_count=views,
                            like_count=likes,
                            is_visible=True,
                        ),
                    )

                self.stdout.write(self.style.SUCCESS(
                    f'  ✅ created  {store.name} ({store.locality}) — '
                    f'{len(store_data["products"])} products, {len(store_data.get("videos", []))} videos'
                ))

            stores[vendor_phone] = store

        self.stdout.write('')

        # ── 3. Customer data: follows, reservations, chats, notifications ─────
        vendor_phones_ordered = [
            '+919000000004',  # Sneha (fashion)
            '+919000000005',  # Vikram (electronics)
            '+919000000007',  # Kiran (footwear)
            '+919000000008',  # Divya (jewellery)
        ]
        chat_categories = ['fashion', 'electronics', 'footwear', 'jewellery']

        customer_phones = [
            p for p, _, role in DEV_USERS if role == 'customer'
        ]

        now = timezone.now()

        for cust_idx, cust_phone in enumerate(customer_phones):
            customer = users[cust_phone]
            cust_name = customer.full_name
            self.stdout.write(f'  Processing {cust_name} ({cust_phone}) …')

            # ── 3a. Follow all dev vendor stores ─────────────────────────────
            for vp in vendor_phones_ordered:
                store = stores[vp]
                StoreFollow.objects.get_or_create(user=customer, store=store)

            # ── 3b. Reservations ──────────────────────────────────────────────
            rotation_idx = min(cust_idx, len(RESERVATION_ROTATION) - 1)
            pend_vp, pend_pi, comp_vp, comp_pi = RESERVATION_ROTATION[rotation_idx]

            for vp, prod_idx, status, expires_delta in [
                (pend_vp, pend_pi, 'pending',   timedelta(hours=2)),
                (comp_vp, comp_pi, 'completed', timedelta(hours=-20)),
            ]:
                store = stores[vp]
                products = list(store.products.filter(status='active'))
                if not products:
                    continue
                product = products[prod_idx % len(products)]
                if not Reservation.objects.filter(customer=customer, product=product).exists():
                    Reservation.objects.create(
                        customer=customer,
                        store=store,
                        product=product,
                        quantity=1,
                        status=status,
                        expires_at=now + expires_delta,
                        note='Dev test reservation',
                    )

            # ── 3c. Conversations with each vendor store ───────────────────────
            for v_idx, vp in enumerate(vendor_phones_ordered):
                store = stores[vp]
                vendor_user = users[vp]
                cat = chat_categories[v_idx]
                script = CHAT_SCRIPTS[cat]

                conv, _ = Conversation.objects.get_or_create(
                    customer=customer, store=store,
                )
                if conv.messages.exists():
                    continue

                for i, (content, sender_role) in enumerate(script):
                    sender = customer if sender_role == 'customer' else vendor_user
                    Message.objects.create(
                        conversation=conv,
                        sender=sender,
                        content=content,
                        message_type='text',
                        is_read=True,
                        created_at=now - timedelta(minutes=(len(script) - i) * 5),
                    )
                # Last vendor message is unread
                last_is_vendor = script[-1][1] == 'vendor'
                conv.unread_count_customer = 1 if last_is_vendor else 0
                conv.last_message_at = now - timedelta(minutes=5)
                conv.save(update_fields=['unread_count_customer', 'last_message_at'])

            # ── 3d. Notifications ─────────────────────────────────────────────
            if not Notification.objects.filter(recipient=customer).exists():
                pending_store = stores[RESERVATION_ROTATION[rotation_idx][0]]
                offer_store   = stores[vendor_phones_ordered[cust_idx % 4]]
                chat_store    = stores[vendor_phones_ordered[(cust_idx + 1) % 4]]

                notifs = [
                    ('reservation_confirmed', 'Reservation Confirmed!',
                     f'Your item at {pending_store.name} is confirmed. Pick up by today 9 PM.',
                     {'store_id': str(pending_store.id)}, False, 0),
                    ('store_opened', f'{pending_store.name} is now open',
                     f'Your followed store just opened. Check out their latest collection!',
                     {'store_id': str(pending_store.id)}, False, 2),
                    ('new_offer', f'New Offer at {offer_store.name}',
                     f'Special deals just launched at {offer_store.name}. Limited time only!',
                     {'store_id': str(offer_store.id)}, True, 4),
                    ('new_message', f'New message from {chat_store.name}',
                     'The vendor replied to your query. Tap to view.',
                     {'store_id': str(chat_store.id)}, True, 6),
                ]
                for ntype, title, body, data, is_read, hours_ago in notifs:
                    Notification.objects.create(
                        recipient=customer,
                        notification_type=ntype,
                        title=title,
                        body=body,
                        data=data,
                        is_read=is_read,
                        created_at=now - timedelta(hours=hours_ago),
                    )

            self.stdout.write(self.style.SUCCESS(f'    ✅ {cust_name}: follows + 2 reservations + 4 chats + 4 notifications'))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═' * 62))
        self.stdout.write(self.style.SUCCESS('  Dev Users Seeded!'))
        self.stdout.write(self.style.SUCCESS('═' * 62))
        rows = [
            ('Arjun Kumar',   '+919000000001', '100001', 'customer'),
            ('Priya Sharma',  '+919000000002', '200002', 'customer'),
            ('Rahul Verma',   '+919000000003', '300003', 'customer'),
            ('Meena Patel',   '+919000000006', '600006', 'customer'),
            ('Sanjay Rao',    '+919000000009', '900009', 'customer'),
            ('Lakshmi Nair',  '+919000000010', '100010', 'customer'),
            ('Sneha Reddy',   '+919000000004', '400004', 'vendor → Sneha\'s Fashion House'),
            ('Vikram Iyer',   '+919000000005', '500005', 'vendor → Vikram Electronics'),
            ('Kiran Naidu',   '+919000000007', '700007', 'vendor → Kiran Footwear Zone'),
            ('Divya Mehta',   '+919000000008', '800008', 'vendor → Divya\'s Jewellery Corner'),
            ('Dev Vendor',    '+919999999999', '999999', 'vendor → NearKart Demo Hub'),
            ('Dev Customer',  '+918888888888', '888888', 'customer'),
        ]
        self.stdout.write(f'  {"Name":<16}  {"Phone":<15}  {"OTP":<8}  Role / Store')
        self.stdout.write(f'  {"─"*16}  {"─"*15}  {"─"*8}  {"─"*30}')
        for name, phone, otp, role in rows:
            self.stdout.write(f'  {name:<16}  {phone:<15}  {otp:<8}  {role}')
        self.stdout.write(self.style.SUCCESS('═' * 62))
        self.stdout.write('  All stores: open Mon–Sat 10:00–21:00, Sunday closed')
        self.stdout.write('  Location: within 2 km of Kukatpally (17.4948, 78.3996)')
        self.stdout.write(self.style.SUCCESS('═' * 62))
