"""
Management command: seed_full_test_data
Creates a complete test dataset for the NearKart app:
  • 1 test customer (phone +917777777777, OTP 123456)
  • Conversations + messages with 5 stores
  • 2 active + 2 past reservations
  • 6 in-app notifications of different types
  • 10 video shorts (one per store)

Run after seed_test_stores:
    docker compose exec web python manage.py seed_full_test_data
    docker compose exec web python manage.py seed_full_test_data --clear
"""
from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone


CUSTOMER_PHONE = '+917777777777'
CUSTOMER_NAME  = 'Test Customer'

# (title, thumbnail_seed, duration_s, description)
VIDEO_DATA = [
    ('New Arrivals at Riya Boutique',       'vid-riya',    45, 'Just dropped — kurtas, palazzos, and anarkalis!'),
    ('Jewellery Unboxing at Lakshmi Jewels','vid-lakshmi', 38, 'Gold sets starting ₹4,999 only this week.'),
    ('Summer Collection at Step Up',        'vid-stepup',  52, 'Sandals, sneakers, and wedges — all on sale.'),
    ('Home Decor Haul at Urban Threads',    'vid-urban',   60, 'Transform your space with our new decor picks.'),
    ('Ethnic Wear Lookbook — Shree Fashion','vid-shree',   41, 'Mix and match kurta sets for every occasion.'),
    ('Kids & Men — Style Hub',              'vid-style',   33, 'Casual and party wear for the whole family.'),
    ('Saree Draping Tutorial — Rani Silk',  'vid-rani',    74, 'Learn 5 styles of draping in under 2 minutes.'),
    ('Diamond Jewellery Showcase',          'vid-golden',  48, 'Certified diamonds, IGI certified, starting ₹8k.'),
    ('Comfort Walk Unboxing',               'vid-comfort', 36, 'Memory foam shoes — wear all day, no pain.'),
    ('Artisan Craft Show — Decor Studio',   'vid-artisan', 57, 'Handmade Dhokra, Madhubani, and blue pottery.'),
]

CONVERSATIONS = [
    # (store_index 0-based, [customer_msg, vendor_msg, ...])
    (0, [  # Riya Boutique
        ('Hi! Do you have the Anarkali Suit in size M?', 'customer'),
        ('Yes! We have it in M and L. The M is our bestseller.', 'vendor'),
        ('Great! What colours are available?', 'customer'),
        ('We have it in Green, Blue, and Rose Pink. All in stock!', 'vendor'),
        ('I would like to reserve the Green M please.', 'customer'),
        ('Done! Reservation created for you. Pick up by 9 PM today.', 'vendor'),
    ]),
    (1, [  # Lakshmi Jewels
        ('Do you have gold necklaces under ₹6,000?', 'customer'),
        ('Yes! We have beautiful gold-plated and gold sets starting ₹2,999.', 'vendor'),
        ('Is hallmarked gold available?', 'customer'),
        ('Absolutely — all our 22k jewellery is BIS hallmarked.', 'vendor'),
    ]),
    (2, [  # Step Up Footwear
        ('Your reservation is confirmed! Sandals in size 7 are held.', 'vendor'),
        ('Thank you! I will come by around 5 PM.', 'customer'),
        ('Perfect, we are open till 9 PM. See you!', 'vendor'),
    ]),
    (4, [  # Shree Fashion Hub
        ('Do you stock mens ethnic wear?', 'customer'),
        ('Yes — kurtas, sherwanis, and dhoti sets. Come check our new collection!', 'vendor'),
    ]),
    (9, [  # Artisan Decor Studio
        ('I love the Dhokra figurines in your video! What is the price range?', 'customer'),
        ('They start from ₹750 and go up to ₹3,500 depending on size and detail.', 'vendor'),
        ('Do you ship within Hyderabad?', 'customer'),
        ('Yes! Free delivery above ₹1,000 within the city.', 'vendor'),
    ]),
]

NOTIFICATIONS = [
    ('reservation', 'Reservation Confirmed!',
     'Your reservation for Anarkali Suit at Riya Boutique is confirmed. Pick up by 9 PM.',
     {'store_id': None, 'product_id': None}),
    ('reservation', 'Reservation Expiring Soon',
     'Your hold on Block Heel Sandals at Step Up Footwear expires in 30 minutes!',
     {'store_id': None, 'product_id': None}),
    ('store_open', 'Riya Boutique is now open',
     'Your favourite store just opened. New kurta collection dropped today!',
     {'store_id': None}),
    ('new_product', 'New Jewellery at Lakshmi Jewels',
     '5 new gold sets just added. Starting ₹2,999 — limited stock!',
     {'store_id': None, 'product_id': None}),
    ('chat', 'New message from Step Up Footwear',
     '"Your reservation is confirmed! Sandals in size 7 are held."',
     {'conversation_id': None}),
    ('offer', 'Weekend Sale — 20% Off',
     'Shree Fashion Hub is offering 20% off on all ethnic wear this weekend.',
     {'store_id': None}),
]


class Command(BaseCommand):
    help = 'Seed complete test data — customer user, chats, reservations, notifications, videos'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Delete previously seeded test customer data before re-seeding')

    def handle(self, *args, **options):
        from apps.auth_app.models import User
        from apps.stores.models import Store
        from apps.products.models import Product
        from apps.chat.models import Conversation, Message
        from apps.reservations.models import Reservation
        from apps.notifications.models import Notification
        from apps.videos.models import Video
        from django.contrib.gis.geos import Point

        # ── Clear if requested ────────────────────────────────────────────────
        if options['clear']:
            User.objects.filter(phone_number=CUSTOMER_PHONE).delete()
            self.stdout.write(self.style.WARNING('Cleared existing test customer data.'))

        # ── 1. Customer user ──────────────────────────────────────────────────
        try:
            customer = User.objects.get(phone_number=CUSTOMER_PHONE)
        except User.DoesNotExist:
            customer = User.objects.create_user(
                phone_number=CUSTOMER_PHONE,
                role='customer',
                full_name=CUSTOMER_NAME,
            )
        self.stdout.write(self.style.SUCCESS(f'✅ Customer: {customer.phone_number} (OTP: 123456)'))

        # ── 2. Ensure stores exist ────────────────────────────────────────────
        stores = list(Store.objects.order_by('created_at')[:10])
        if len(stores) < 5:
            self.stdout.write(self.style.ERROR(
                '❌ Not enough stores found. Run seed_test_stores first:\n'
                '   python manage.py seed_test_stores'
            ))
            return

        # ── 3. Conversations + messages ───────────────────────────────────────
        conversations_created = []
        for store_idx, msgs in CONVERSATIONS:
            if store_idx >= len(stores):
                continue
            store = stores[store_idx]
            vendor_user = store.owner

            conv, _ = Conversation.objects.get_or_create(
                customer=customer, store=store,
            )
            conversations_created.append(conv)

            if not conv.messages.exists():
                now = timezone.now()
                for i, (content, role) in enumerate(msgs):
                    sender = customer if role == 'customer' else vendor_user
                    msg_time = now - timedelta(minutes=(len(msgs) - i) * 3)
                    Message.objects.create(
                        conversation=conv,
                        sender=sender,
                        content=content,
                        message_type='text',
                        is_read=True,
                        created_at=msg_time,
                    )
                # Mark unread count (last vendor message unread for customer)
                last_vendor = [m for _, m in enumerate(msgs) if m[1] == 'vendor']
                if last_vendor:
                    conv.unread_count_customer = 1
                conv.last_message_at = timezone.now()
                conv.save()

        self.stdout.write(self.style.SUCCESS(f'✅ {len(conversations_created)} conversations seeded'))

        # ── 4. Reservations ───────────────────────────────────────────────────
        # Get products from the first two stores
        products_s0 = list(stores[0].products.filter(status='active')[:2])
        products_s2 = list(stores[2].products.filter(status='active')[:2])

        now = timezone.now()
        reservations_data = []

        if len(products_s0) >= 2 and len(products_s2) >= 2:
            reservations_data = [
                # Active: expires in ~2 hours
                (stores[0], products_s0[0], 'pending',   now + timedelta(hours=2)),
                # Active: expiring soon
                (stores[2], products_s2[0], 'confirmed', now + timedelta(minutes=28)),
                # Past: completed yesterday
                (stores[0], products_s0[1], 'completed', now - timedelta(hours=20)),
                # Past: cancelled 2 hours ago
                (stores[2], products_s2[1], 'cancelled', now - timedelta(hours=2)),
            ]
        elif products_s0:
            # Fallback: use whatever products exist
            for i, p in enumerate(products_s0[:2]):
                status = 'pending' if i == 0 else 'completed'
                expires = now + timedelta(hours=2) if i == 0 else now - timedelta(hours=20)
                reservations_data.append((stores[0], p, status, expires))

        res_created = 0
        for store, product, status, expires_at in reservations_data:
            if not Reservation.objects.filter(customer=customer, product=product).exists():
                Reservation.objects.create(
                    customer=customer,
                    store=store,
                    product=product,
                    quantity=1,
                    status=status,
                    expires_at=expires_at,
                    note='Test reservation',
                )
                res_created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ {res_created} reservations seeded (2 active, 2 past)'))

        # ── 5. Notifications ──────────────────────────────────────────────────
        if not Notification.objects.filter(recipient=customer).exists():
            conv_id = conversations_created[2].id if len(conversations_created) > 2 else None

            notif_payloads = [
                ('reservation_confirmed', 'Reservation Confirmed!',
                 'Your reservation for Anarkali Suit at Riya Boutique is confirmed. Pick up by 9 PM.',
                 {'store_id': str(stores[0].id)}),
                ('reservation_created', 'Reservation Expiring Soon',
                 'Your hold on Block Heel Sandals at Step Up Footwear expires in 30 minutes!',
                 {'store_id': str(stores[2].id)}),
                ('store_opened', 'Riya Boutique is now open',
                 'Your favourite store just opened. New kurta collection dropped today!',
                 {'store_id': str(stores[0].id)}),
                ('new_message', 'New message from Step Up Footwear',
                 '"Your reservation is confirmed! Sandals in size 7 are held."',
                 {'conversation_id': str(conv_id) if conv_id else ''}),
                ('group_product_shared', 'Weekend Sale — 20% Off',
                 'Shree Fashion Hub is offering 20% off on all ethnic wear this weekend.',
                 {'store_id': str(stores[4].id) if len(stores) > 4 else ''}),
                ('new_message', 'New message from Lakshmi Jewels',
                 '"All our 22k jewellery is BIS hallmarked."',
                 {'conversation_id': str(conversations_created[1].id) if len(conversations_created) > 1 else ''}),
            ]

            for i, (ntype, title, body, data) in enumerate(notif_payloads):
                Notification.objects.create(
                    recipient=customer,
                    notification_type=ntype,
                    title=title,
                    body=body,
                    data=data,
                    is_read=(i >= 3),
                    created_at=now - timedelta(hours=i * 2),
                )

            self.stdout.write(self.style.SUCCESS(f'✅ 6 notifications seeded (3 unread)'))
        else:
            self.stdout.write(f'   Notifications already exist, skipping.')

        # ── 6. Videos (one per store) ─────────────────────────────────────────
        # Use a publicly available test HLS stream and picsum thumbnails
        TEST_HLS_URL = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'

        vids_created = 0
        for i, store in enumerate(stores[:10]):
            if store.videos.filter(status='ready').exists():
                continue
            if i >= len(VIDEO_DATA):
                break
            title, thumb_seed, duration, description = VIDEO_DATA[i]
            Video.objects.create(
                store=store,
                title=title,
                description=description,
                thumbnail_url=f'https://picsum.photos/seed/{thumb_seed}/400/700',
                video_url=TEST_HLS_URL,
                status='ready',
                duration_seconds=duration,
                location=store.location,
                locality=store.locality,
                view_count=max(0, (i + 1) * 47 - i * 11),
                like_count=max(0, (i + 1) * 12 - i * 3),
            )
            vids_created += 1

        self.stdout.write(self.style.SUCCESS(f'✅ {vids_created} videos seeded'))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═' * 55))
        self.stdout.write(self.style.SUCCESS('  NearKart Full Test Data Seeded!'))
        self.stdout.write(self.style.SUCCESS('═' * 55))
        self.stdout.write(f'  Customer phone : {CUSTOMER_PHONE}')
        self.stdout.write(f'  OTP (dev mode) : 123456')
        self.stdout.write(f'  Role           : customer')
        self.stdout.write(f'  Conversations  : {len(conversations_created)} (with 5 stores)')
        self.stdout.write(f'  Reservations   : {res_created} (2 active, 2 past)')
        self.stdout.write(f'  Notifications  : 6 (3 unread, 3 read)')
        self.stdout.write(f'  Videos         : {vids_created} (one per store, HLS stream)')
        self.stdout.write(self.style.SUCCESS('═' * 55))
