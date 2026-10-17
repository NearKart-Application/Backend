"""
Management command: seed_city_broadcast_posts
Creates 1–3 posts per BroadcastChannel for seeded stores (phones starting '+917').
Channels that already have posts are skipped (safe to re-run).
"""
import random
from django.core.management.base import BaseCommand
from apps.stores.models import Store, BroadcastChannel, BroadcastPost


POSTS_BY_CATEGORY = {
    'fashion': [
        'New collection just dropped! Kurtas, sarees, and lehengas — fresh designs for the season. Come visit us today!',
        'Festive season is here! Check out our exclusive ethnic wear collection. Limited stock — don\'t miss out!',
        'Summer clearance sale is live. Up to 30% off on selected items. Visit the store before stocks run out.',
        'We just received a stunning new batch of designer salwar suits. First come, first served!',
        'Thank you for your love and support! As a token of appreciation, enjoy special offers this week.',
        'Our wedding collection is now available. Bridal lehengas, sherwanis, and more — come see in-store.',
        'Weekend special: Buy any 2 items and get the third at 50% off. Valid this Saturday and Sunday only!',
    ],
    'jewellery': [
        'Gold rate update for today: Check our latest prices. Walk in for the best making charges in the area!',
        'New bridal jewellery collection arrived! Temple jewellery, gold sets, and more — perfect for weddings.',
        'Exchange your old jewellery and upgrade to our latest designs. Best rates guaranteed!',
        'Lightweight daily wear gold collection now available. Perfect for everyday elegance.',
        'Silver jewellery sale is here — anklets, bangles, and rings at unbeatable prices.',
        'Our artisan team has crafted a special festive collection — only 50 pieces available!',
        'Diamond anniversary collection is live! Treat your loved ones this season.',
    ],
    'footwear': [
        'New season arrivals just in! Sandals, loafers, sneakers — something for everyone.',
        'Monsoon sale is live! Waterproof footwear at special prices. Stay stylish in the rain.',
        'Sports and casual collection restocked. Come pick your favourite pair today!',
        'Kids back-to-school footwear now available. Durable, comfortable, and affordable.',
        'Buy 1 get 1 at 50% off — this week only! Visit us in-store to grab the deal.',
        'Formal leather shoes sale — premium quality at clearance prices. Sizes going fast!',
        'Our new women\'s heels collection is here. Elegant, comfortable, and trendy.',
    ],
    'decor': [
        'New handmade décor collection just arrived! Wall art, vases, torans, and more.',
        'Festive décor is here — diyas, lanterns, and floor rangoli kits at special prices.',
        'Transform your living room with our curated collection. Visit us for a free consultation!',
        'Garden and balcony décor sale is live. Pots, plant stands, and outdoor accessories.',
        'Looking for a unique housewarming gift? Check out our ready-to-gift décor sets.',
        'New wall art frames collection — custom sizing available. Order yours today!',
        'Our interior design team is now taking consultation bookings — come visit us!',
    ],
    'furniture': [
        'New living room collection is here! Sofas, coffee tables, and bookshelves — visit us today.',
        'Bedroom furniture sale: Complete sets at flat discount. Limited stock available.',
        'Custom furniture orders now open! Get furniture made to your exact measurements.',
        'Work-from-home furniture — ergonomic chairs and study tables now in stock.',
        'Kids room furniture collection launched. Safe, colourful, and durable designs.',
        'Storage solutions sale is live — wardrobes, cabinets, and modular shelves.',
        'Our new showroom wing is now open! Come explore 200+ furniture designs.',
    ],
    'gifts': [
        'New personalised gift range is here — custom mugs, frames, keepsakes, and more!',
        'Wedding season is here! Explore our curated gift hampers for couples.',
        'Birthday bundles ready to go — gifts wrapped and packed, just pick up or order.',
        'Corporate gifting made easy — bulk orders accepted with free branding.',
        'Diwali gift hampers now available! Order early to avoid last-minute rush.',
        'Same-day delivery available for orders placed before noon within the area.',
        'Surprise someone special today — browse our new arrivals in-store or call us!',
    ],
    'beauty': [
        'New skincare collection just arrived — serums, moisturisers, and sunscreens from top brands.',
        'Makeup sale is live! Lipsticks, foundations, and eye palettes at special prices.',
        'Natural and organic beauty range is now available. Chemical-free, skin-friendly products.',
        'Men\'s grooming kits restocked — face wash, moisturiser, beard oil, and more.',
        'Buy any 3 beauty products and get a free mini-kit — this week only!',
        'Hair care special: Shampoos, conditioners, and hair masks at flat discount.',
        'Festive glow kit is here — complete routine for glowing skin this season!',
    ],
    'food': [
        'Today\'s special: Fresh homemade biryani and curry — order now, limited quantity!',
        'Weekly tiffin subscription now open! Healthy home-style food delivered to your door.',
        'New breakfast combo available every morning — idli, dosa, and poha at special prices.',
        'Family meal combos launched! Feed your family wholesome food at affordable rates.',
        'Festive sweet boxes now available — kaju katli, ladoos, and more. Pre-order yours!',
        'Evening snack combo: Tea + samosas + snack at a special evening deal price.',
        'Weekend special menu is here! Extra dishes, bigger portions — come dine with us.',
    ],
    'electronics': [
        'New mobile accessories just arrived — covers, chargers, earphones from top brands.',
        'Smart TV sale is live! Latest models at exchange prices — limited stock.',
        'Laptop collection restocked for students and professionals. EMI available!',
        'Gaming accessories sale — controllers, headsets, and keyboards at special prices.',
        'Free screen guard with every mobile purchase this week — walk in today!',
        'Home appliances offer: ACs and refrigerators at festive discount prices.',
        'We now offer mobile repair services! Quick turnaround, genuine parts.',
    ],
}


class Command(BaseCommand):
    help = 'Add 1–3 posts to each BroadcastChannel for seeded stores (phones +917…)'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all posts from seeded channels first')
        parser.add_argument('--min', type=int, default=1, help='Min posts per channel (default 1)')
        parser.add_argument('--max', type=int, default=3, help='Max posts per channel (default 3)')

    def handle(self, *args, **options):
        seeded_stores = Store.objects.filter(phone__startswith='+917')
        channels = list(
            BroadcastChannel.objects.filter(store__in=seeded_stores).select_related('store').only('id', 'store__category')
        )
        total_channels = len(channels)

        if options['clear']:
            self.stdout.write('Clearing seeded broadcast posts…')
            deleted, _ = BroadcastPost.objects.filter(channel__in=channels).delete()
            self.stdout.write(f'Deleted {deleted} posts.')

        already_has = set(
            BroadcastPost.objects.filter(channel__in=channels).values_list('channel_id', flat=True)
        )

        min_posts = max(1, options['min'])
        max_posts = min(3, max(min_posts, options['max']))

        to_create = []
        skipped = 0
        for channel in channels:
            if channel.id in already_has:
                skipped += 1
                continue
            category = channel.store.category
            templates = POSTS_BY_CATEGORY.get(category, POSTS_BY_CATEGORY['fashion'])
            count = random.randint(min_posts, max_posts)
            chosen = random.sample(templates, min(count, len(templates)))
            for content in chosen:
                to_create.append(BroadcastPost(channel=channel, content=content, image_url=''))

        if not to_create:
            self.stdout.write(self.style.SUCCESS(
                f'All {total_channels} channels already have posts. Nothing to do.'
            ))
            return

        BroadcastPost.objects.bulk_create(to_create, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅  Done! Created {len(to_create)} posts across '
            f'{total_channels - skipped} channels ({skipped} already had posts).'
        ))
        self.stdout.write('   To reset: python manage.py seed_city_broadcast_posts --clear')
