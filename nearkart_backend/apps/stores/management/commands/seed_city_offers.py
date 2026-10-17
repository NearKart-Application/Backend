"""
Management command: seed_city_offers
Creates 1–5 offers per seeded store (phones starting '+917').
Stores that already have offers are skipped (safe to re-run).
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from apps.stores.models import Store, StoreOffer


# Category-specific offer templates: (title, description, discount_pct)
OFFER_TEMPLATES = {
    'fashion': [
        ('New Arrivals Sale', 'Fresh ethnic & western wear — kurtas, sarees, lehengas at special prices.', 15),
        ('Festive Collection', 'Get festive-ready with our exclusive collection. Limited stock!', 20),
        ('Summer Clearance', 'End-of-season clearance on all summer wear.', 30),
        ('Buy 2 Get 1 Free', 'Purchase any 2 items and get the third absolutely free.', None),
        ('Grand Sale', 'Massive discounts on top brands — hurry, limited time offer!', 25),
        ('Women\'s Special', 'Exclusive discounts on women\'s ethnic wear this week only.', 20),
        ('Designer Wear Offer', 'Flat discount on all designer collections — premium style, pocket-friendly price.', 10),
    ],
    'jewellery': [
        ('Gold Rate Offer', 'Buy gold jewellery today at today\'s special making charges.', None),
        ('Silver Collection Sale', 'Flat discount on all silver jewellery — rings, bangles, anklets.', 15),
        ('Festive Jewellery Offer', 'Handcrafted temple jewellery at festive prices.', 10),
        ('Diamond Studded Deal', 'Special making-charge waiver on diamond jewellery.', None),
        ('Exchange & Upgrade', 'Exchange your old jewellery and upgrade at discounted rates.', 20),
        ('Bridal Special', 'Complete bridal sets at exclusive prices — gold, silver, and more.', 12),
        ('Daily Wear Offer', 'Lightweight daily wear jewellery at unbeatable prices.', 18),
    ],
    'footwear': [
        ('Monsoon Sale', 'Waterproof and casual footwear at monsoon prices.', 20),
        ('Sports Collection Offer', 'Flat discount on all sports shoes and sneakers.', 25),
        ('Buy 1 Get 1 Half Price', 'Buy any footwear and get the second pair at 50% off.', None),
        ('New Season Arrivals', 'Fresh footwear collection just arrived — sandals, heels, loafers.', 15),
        ('Formal Shoes Sale', 'Premium leather formal shoes at discounted rates.', 20),
        ('Kids Footwear Deal', 'Flat discount on all kids footwear — school shoes, sandals, sneakers.', 30),
        ('End of Season', 'Up to 40% off on last season\'s collection — limited sizes.', 40),
    ],
    'decor': [
        ('Home Makeover Sale', 'Refresh your home with handcrafted décor at special prices.', 20),
        ('Festive Décor Offer', 'Diyas, lanterns, torans, and more at festive prices.', 15),
        ('Wall Art Collection', 'Flat discount on all wall art and frames.', 25),
        ('Handmade Special', 'Exclusive handmade décor items — unique and affordable.', 10),
        ('Interior Bundle Deal', 'Buy a décor set and save extra.', 20),
        ('Garden Décor Sale', 'Outdoor and garden décor at unbeatable prices.', 30),
        ('Gifting Set Offer', 'Ready-to-gift décor sets at special prices.', 15),
    ],
    'furniture': [
        ('Living Room Sale', 'Sofas, coffee tables and shelves at special prices.', 15),
        ('Bedroom Furniture Offer', 'Complete bedroom sets — bed, wardrobe, dresser at flat discount.', 20),
        ('Study Table Deal', 'Ergonomic study tables and chairs at student-friendly prices.', 25),
        ('Storage Solutions Sale', 'Cabinets, shelves, and wardrobes at clearance prices.', 30),
        ('Custom Furniture Offer', 'Get custom furniture made at special introductory rates.', 10),
        ('Office Furniture Discount', 'Work-from-home furniture at flat discounted rates.', 20),
        ('Kids Room Sale', 'Bunk beds, study desks, and kids furniture at special prices.', 25),
    ],
    'gifts': [
        ('Birthday Bundle Offer', 'Complete gift bundles — wrapping included at no extra charge.', None),
        ('Personalized Gifts Sale', 'Customized mugs, frames, and keepsakes at special prices.', 15),
        ('Wedding Gift Offer', 'Curated wedding gift hampers at flat discount.', 20),
        ('Seasonal Gift Sale', 'Special occasion gifts — Diwali, Holi, Eid hampers at reduced prices.', 25),
        ('Combo Gift Deal', 'Buy 2 gift hampers and get extra discount.', 30),
        ('Corporate Gift Offer', 'Bulk corporate gifts at negotiated rates — contact us.', None),
        ('Same Day Delivery', 'Order before noon and get same-day delivery for gifts in your area.', None),
    ],
    'beauty': [
        ('Skincare Kit Sale', 'Complete skincare routine kits at special bundled prices.', 20),
        ('Hair Care Offer', 'Shampoos, serums, and hair masks at flat discount.', 25),
        ('Makeup Sale', 'Lipsticks, foundations, and eye products at clearance prices.', 30),
        ('Natural & Organic Sale', 'All-natural beauty products at introductory prices.', 15),
        ('Combo Beauty Deal', 'Buy any 3 products and get a free mini-kit.', None),
        ('Men\'s Grooming Offer', 'Grooming kits and skincare for men at flat discount.', 20),
        ('Festive Glow Kit', 'Get festive-ready with our special glow kit at a special price.', 15),
    ],
    'food': [
        ('Lunch Box Special', 'Order a weekly tiffin subscription and save on every meal.', 15),
        ('Family Combo Offer', 'Family meal combos at flat discounted rates.', 20),
        ('Breakfast Deal', 'Fresh breakfast combos every morning at special prices.', None),
        ('Sweets & Snacks Sale', 'Festive sweets and homemade snacks at special prices.', 10),
        ('Bulk Order Discount', 'Order for 5+ people and get flat discount on total bill.', 25),
        ('Evening Snack Combo', 'Tea + snacks combo deal — perfect for evenings.', None),
        ('Weekend Special', 'Special weekend-only menu at reduced prices.', 15),
    ],
    'electronics': [
        ('Mobile Accessories Sale', 'Covers, chargers, earphones, and more at flat discount.', 20),
        ('Smart TV Offer', 'Latest smart TVs at special exchange prices.', 15),
        ('Laptop Deal', 'Student and professional laptops at EMI-friendly rates with cashback.', 10),
        ('Audio Sale', 'Earbuds, headphones, and speakers at clearance prices.', 30),
        ('Gaming Offer', 'Gaming accessories — controllers, headsets at special prices.', 25),
        ('Home Appliances Discount', 'ACs, washing machines, refrigerators at festive prices.', 15),
        ('Screen Guard Free', 'Get a free screen guard with every mobile purchase.', None),
    ],
}


class Command(BaseCommand):
    help = 'Add 1–5 offers to every seeded store (phones +917…) that has none'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all offers from seeded stores first')
        parser.add_argument('--min', type=int, default=1, help='Min offers per store (default 1)')
        parser.add_argument('--max', type=int, default=5, help='Max offers per store (default 5)')

    def handle(self, *args, **options):
        seeded_stores = Store.objects.filter(phone__startswith='+917').only('id', 'name', 'category')
        total = seeded_stores.count()

        if options['clear']:
            self.stdout.write('Clearing seeded store offers…')
            deleted, _ = StoreOffer.objects.filter(store__in=seeded_stores).delete()
            self.stdout.write(f'Deleted {deleted} offers.')

        already_has = set(
            StoreOffer.objects.filter(store__in=seeded_stores).values_list('store_id', flat=True)
        )

        min_offers = max(1, options['min'])
        max_offers = min(5, max(min_offers, options['max']))
        today = date.today()

        to_create = []
        skipped = 0
        for store in seeded_stores:
            if store.id in already_has:
                skipped += 1
                continue
            templates = OFFER_TEMPLATES.get(store.category, OFFER_TEMPLATES['fashion'])
            count = random.randint(min_offers, max_offers)
            chosen = random.sample(templates, min(count, len(templates)))
            for title, description, discount_pct in chosen:
                # valid_till: 60–180 days from today; 30% chance of no expiry
                valid_till = None if random.random() < 0.3 else today + timedelta(days=random.randint(60, 180))
                to_create.append(StoreOffer(
                    store        = store,
                    title        = title,
                    description  = description,
                    discount_pct = discount_pct,
                    valid_till   = valid_till,
                    is_active    = True,
                ))

        if not to_create:
            self.stdout.write(self.style.SUCCESS(
                f'All {total} seeded stores already have offers. Nothing to do.'
            ))
            return

        StoreOffer.objects.bulk_create(to_create, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅  Done! Created {len(to_create)} offers across '
            f'{total - skipped} stores ({skipped} already had offers).'
        ))
        self.stdout.write('   To reset: python manage.py seed_city_offers --clear')
