"""
Management command: seed_test_stores
Creates 10 vendor-owned stores near Kukatpally, Hyderabad,
each with 10 active products, images, size variants, and store hours.

Usage:
    docker compose exec web python manage.py seed_test_stores
    docker compose exec web python manage.py seed_test_stores --clear
"""
import uuid
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from datetime import time


STORES = [
    {
        'phone': '+919800000001',
        'name': 'Riya Boutique',
        'category': 'fashion',
        'description': 'Trendy ethnic wear — kurtas, sarees, and lehengas at unbeatable prices.',
        'address': 'Plot 12, KPHB Phase 1, Kukatpally, Hyderabad',
        'locality': 'Kukatpally',
        'lat': 17.4948, 'lng': 78.3996,
        'logo': 'https://picsum.photos/seed/store-riya/200/200',
        'banner': 'https://picsum.photos/seed/banner-riya/800/300',
        'products': [
            ('Blue Cotton Kurta',       'clothing', 450,  380, ['S', 'M', 'L', 'XL'], '#1D4ED8'),
            ('Red Silk Saree',          'clothing', 1800, None, [],                    '#DC2626'),
            ('Embroidered Dupatta',     'clothing', 350,  None, ['Free Size'],         '#7C3AED'),
            ('Anarkali Suit',           'clothing', 1200, 999, ['S', 'M', 'L'],       '#059669'),
            ('Printed Palazzo Set',     'clothing', 650,  None, ['S', 'M', 'L', 'XL'], '#F59E0B'),
            ('Linen Straight Kurta',    'clothing', 580,  None, ['XS', 'S', 'M', 'L'], '#6B7280'),
            ('Floral Maxi Dress',       'clothing', 799,  649, ['S', 'M', 'L'],       '#EC4899'),
            ('Tie-Dye Kurti',           'clothing', 420,  None, ['S', 'M', 'L', 'XL'], '#8B5CF6'),
            ('Georgette Party Gown',    'clothing', 2200, None, ['S', 'M', 'L'],       '#F97316'),
            ('Cotton Salwar Set',       'clothing', 780,  None, ['XS', 'S', 'M', 'L', 'XL'], '#0EA5E9'),
        ],
    },
    {
        'phone': '+919800000002',
        'name': 'Lakshmi Jewels',
        'category': 'jewellery',
        'description': 'Handcrafted gold, silver, and temple jewellery for every occasion.',
        'address': 'Shop 5, KPHB Colony, Hyderabad',
        'locality': 'KPHB',
        'lat': 17.4972, 'lng': 78.3944,
        'logo': 'https://picsum.photos/seed/store-lakshmi/200/200',
        'banner': 'https://picsum.photos/seed/banner-lakshmi/800/300',
        'products': [
            ('Gold Jhumka Earrings',    'jewellery', 1200, None, [],  '#F59E0B'),
            ('Diamond Pendant Necklace','jewellery', 8500, 7999, [], '#60A5FA'),
            ('Silver Bangles Set',      'jewellery', 450,  None, [],  '#9CA3AF'),
            ('Pearl Stud Earrings',     'jewellery', 650,  None, [],  '#F3F4F6'),
            ('Kundan Bridal Set',       'jewellery', 3200, None, [],  '#FCD34D'),
            ('Temple Necklace',         'jewellery', 1800, 1499, [], '#EF4444'),
            ('Oxidized Finger Ring',    'jewellery', 280,  None, ['6', '7', '8'], '#6B7280'),
            ('Bridal Maang Tikka',      'jewellery', 950,  None, [],  '#F59E0B'),
            ('Ruby Pendant',            'jewellery', 2100, None, [],  '#DC2626'),
            ('Emerald Bracelet',        'jewellery', 1650, None, [],  '#059669'),
        ],
    },
    {
        'phone': '+919800000003',
        'name': 'Step Up Footwear',
        'category': 'footwear',
        'description': 'Comfortable and stylish footwear for every step of life.',
        'address': 'Shop 3, Bachupally Main Road, Hyderabad',
        'locality': 'Bachupally',
        'lat': 17.5012, 'lng': 78.3988,
        'logo': 'https://picsum.photos/seed/store-stepup/200/200',
        'banner': 'https://picsum.photos/seed/banner-stepup/800/300',
        'products': [
            ('White Canvas Sneakers',   'footwear', 699,  549, ['6', '7', '8', '9', '10'], '#F9FAFB'),
            ('Brown Leather Loafers',   'footwear', 1200, None, ['6', '7', '8', '9'],     '#92400E'),
            ('Kolhapuri Chappals',      'footwear', 480,  None, ['5', '6', '7', '8'],     '#D97706'),
            ('Block Heel Pumps',        'footwear', 899,  749, ['5', '6', '7', '8'],      '#BE185D'),
            ('Running Sports Shoes',    'footwear', 1500, None, ['6', '7', '8', '9', '10'], '#2563EB'),
            ('Ankle Strap Sandals',     'footwear', 650,  None, ['5', '6', '7', '8'],     '#7C3AED'),
            ('Classic Oxford Shoes',    'footwear', 1800, 1499, ['6', '7', '8', '9'],     '#1F2937'),
            ('Wedge Espadrilles',       'footwear', 750,  None, ['5', '6', '7', '8'],     '#F59E0B'),
            ('Slip-On Mules',           'footwear', 520,  None, ['5', '6', '7'],           '#EC4899'),
            ('Chelsea Ankle Boots',     'footwear', 2100, None, ['6', '7', '8', '9'],     '#374151'),
        ],
    },
    {
        'phone': '+919800000004',
        'name': 'Home Decor World',
        'category': 'decor',
        'description': 'Unique handmade décor to transform your living space.',
        'address': '14, Miyapur Road, Hyderabad',
        'locality': 'Miyapur',
        'lat': 17.4905, 'lng': 78.4021,
        'logo': 'https://picsum.photos/seed/store-homedecor/200/200',
        'banner': 'https://picsum.photos/seed/banner-homedecor/800/300',
        'products': [
            ('Wooden Floating Wall Shelf', 'decor', 890,  749, [],   '#92400E'),
            ('Boho Cushion Cover Set',     'decor', 450,  None, [],   '#F59E0B'),
            ('Ceramic Flower Vase',        'decor', 380,  None, [],   '#6EE7B7'),
            ('Macrame Wall Hanging',       'decor', 650,  None, [],   '#FDE68A'),
            ('Bamboo Table Lamp',          'decor', 1200, 999, [],    '#D97706'),
            ('Moroccan Iron Lantern',      'decor', 780,  None, [],   '#F97316'),
            ('Rattan Storage Basket',      'decor', 550,  None, [],   '#D97706'),
            ('Lavender Scented Candle Set','decor', 350,  None, [],   '#DDD6FE'),
            ('Collage Photo Frame Set',    'decor', 480,  None, [],   '#374151'),
            ('Hand-Woven Table Runner',    'decor', 320,  None, [],   '#FDE68A'),
        ],
    },
    {
        'phone': '+919800000005',
        'name': 'Shree Fashion Hub',
        'category': 'fashion',
        'description': 'Contemporary western and fusion fashion for the modern woman.',
        'address': 'Shop 22, Madhapur, Hyderabad',
        'locality': 'Madhapur',
        'lat': 17.4885, 'lng': 78.3968,
        'logo': 'https://picsum.photos/seed/store-shree/200/200',
        'banner': 'https://picsum.photos/seed/banner-shree/800/300',
        'products': [
            ('Denim Jacket',            'clothing', 1299, 999, ['S', 'M', 'L', 'XL'], '#1D4ED8'),
            ('Oversized Hoodie',        'clothing', 799,  None, ['S', 'M', 'L', 'XL'], '#374151'),
            ('Jogger Track Pants',      'clothing', 599,  None, ['S', 'M', 'L', 'XL'], '#6B7280'),
            ('Crop Tank Top',           'clothing', 299,  249, ['XS', 'S', 'M'],       '#F9A8D4'),
            ('Bomber Jacket',           'clothing', 1499, None, ['S', 'M', 'L'],       '#059669'),
            ('High-Waist Leggings',     'clothing', 449,  None, ['S', 'M', 'L', 'XL'], '#1F2937'),
            ('Ethnic Embroidered Jacket','clothing', 1800, None, ['S', 'M', 'L'],      '#7C3AED'),
            ('Wrap Dress',              'clothing', 899,  749, ['S', 'M', 'L'],        '#EC4899'),
            ('Flared Bell Bottom',      'clothing', 699,  None, ['S', 'M', 'L', 'XL'], '#374151'),
            ('Shirt Dress',             'clothing', 999,  None, ['S', 'M', 'L'],       '#60A5FA'),
        ],
    },
    {
        'phone': '+919800000006',
        'name': 'Anjali Collections',
        'category': 'fashion',
        'description': 'Premium silk and chiffon sarees, lehengas, and party wear.',
        'address': 'Gachibowli Circle, Hyderabad',
        'locality': 'Gachibowli',
        'lat': 17.4925, 'lng': 78.4052,
        'logo': 'https://picsum.photos/seed/store-anjali/200/200',
        'banner': 'https://picsum.photos/seed/banner-anjali/800/300',
        'products': [
            ('Georgette Printed Saree',  'clothing', 1400, 1199, [], '#EC4899'),
            ('Chiffon Embroidered Dupatta','clothing', 450, None, ['Free Size'], '#A78BFA'),
            ('Cotton Lehenga Choli',     'clothing', 2200, None, ['S', 'M', 'L'], '#F59E0B'),
            ('Velvet Blouse',            'clothing', 699,  None, ['32', '34', '36', '38'], '#7C3AED'),
            ('Zardosi Work Kurta',       'clothing', 1599, 1299, ['S', 'M', 'L', 'XL'], '#EF4444'),
            ('Net Party Saree',          'clothing', 1800, None, [], '#60A5FA'),
            ('Pure Silk Saree',          'clothing', 4500, None, [], '#F97316'),
            ('Banarasi Dupatta',         'clothing', 850,  None, ['Free Size'], '#FCD34D'),
            ('Kalamkari Print Top',      'clothing', 680,  None, ['S', 'M', 'L', 'XL'], '#D97706'),
            ('Block Print Co-ord Set',   'clothing', 1199, 999, ['S', 'M', 'L'], '#059669'),
        ],
    },
    {
        'phone': '+919800000007',
        'name': 'Rani Silk Sarees',
        'category': 'fashion',
        'description': 'Handloom and silk sarees from across India — Kanjivaram, Banarasi, Tussar.',
        'address': '8, Kondapur Road, Hyderabad',
        'locality': 'Kondapur',
        'lat': 17.4960, 'lng': 78.3912,
        'logo': 'https://picsum.photos/seed/store-rani/200/200',
        'banner': 'https://picsum.photos/seed/banner-rani/800/300',
        'products': [
            ('Kanjivaram Silk Saree',   'clothing', 6500, None, [], '#7C3AED'),
            ('Mysore Crepe Silk Saree', 'clothing', 3200, 2799, [], '#F59E0B'),
            ('Pure Cotton Handloom',    'clothing', 980,  None, [], '#059669'),
            ('Tussar Silk Saree',       'clothing', 2800, None, [], '#D97706'),
            ('Ikkat Woven Saree',       'clothing', 1900, 1599, [], '#1D4ED8'),
            ('Patola Silk Saree',       'clothing', 5500, None, [], '#EC4899'),
            ('Jamdani Muslin Saree',    'clothing', 3800, None, [], '#6EE7B7'),
            ('Baluchari Brocade Saree', 'clothing', 4200, 3699, [], '#EF4444'),
            ('Chanderi Cotton Saree',   'clothing', 1200, None, [], '#F9A8D4'),
            ('Gadwal Silk Saree',       'clothing', 4800, None, [], '#FCD34D'),
        ],
    },
    {
        'phone': '+919800000008',
        'name': 'Golden Touch Jewellery',
        'category': 'jewellery',
        'description': 'Designer and diamond jewellery — rings, necklaces, and bridal sets.',
        'address': 'Hitech City Road, Hyderabad',
        'locality': 'Hitech City',
        'lat': 17.5005, 'lng': 78.4010,
        'logo': 'https://picsum.photos/seed/store-golden/200/200',
        'banner': 'https://picsum.photos/seed/banner-golden/800/300',
        'products': [
            ('Solitaire Diamond Ring',  'jewellery', 12000, None, ['6', '7', '8'], '#E5E7EB'),
            ('Gold Chain Necklace',     'jewellery', 5500, None, [],              '#F59E0B'),
            ('Platinum Wedding Band',   'jewellery', 8500, None, ['6', '7', '8', '9'], '#E5E7EB'),
            ('Rose Gold Hoop Earrings', 'jewellery', 2200, 1899, [],              '#FCA5A5'),
            ('White Gold Bracelet',     'jewellery', 4500, None, [],              '#F3F4F6'),
            ('Blue Sapphire Pendant',   'jewellery', 3800, None, [],              '#2563EB'),
            ('Ruby and Diamond Set',    'jewellery', 15000, None, [],             '#DC2626'),
            ('Emerald Cocktail Ring',   'jewellery', 5200, 4599, ['6', '7', '8'], '#059669'),
            ('Coral Bead Necklace',     'jewellery', 1800, None, [],              '#F97316'),
            ('Blue Topaz Earrings',     'jewellery', 2600, None, [],              '#60A5FA'),
        ],
    },
    {
        'phone': '+919800000009',
        'name': 'Comfort Foot Store',
        'category': 'footwear',
        'description': 'Ergonomic and stylish footwear — sports, formal, and casual.',
        'address': 'Patancheru Main Road, Hyderabad',
        'locality': 'Patancheru',
        'lat': 17.4855, 'lng': 78.4032,
        'logo': 'https://picsum.photos/seed/store-comfort/200/200',
        'banner': 'https://picsum.photos/seed/banner-comfort/800/300',
        'products': [
            ('Memory Foam Walking Shoes', 'footwear', 1199, 999, ['6', '7', '8', '9', '10'], '#374151'),
            ('Suede Chelsea Loafers',     'footwear', 1599, None, ['6', '7', '8', '9'],      '#92400E'),
            ('Arch Support Sandals',      'footwear', 780,  None, ['5', '6', '7', '8'],      '#D97706'),
            ('Cork Footbed Flats',        'footwear', 650,  None, ['5', '6', '7', '8'],      '#FDE68A'),
            ('Cushioned Running Shoes',   'footwear', 1899, 1499, ['6', '7', '8', '9', '10'], '#3B82F6'),
            ('Platform Sneakers',         'footwear', 1299, None, ['5', '6', '7', '8'],      '#F9FAFB'),
            ('Leather Mule Slides',       'footwear', 799,  None, ['5', '6', '7', '8'],      '#92400E'),
            ('Waterproof Ankle Boots',    'footwear', 2200, None, ['6', '7', '8', '9'],      '#1F2937'),
            ('Breathable Canvas Shoes',   'footwear', 549,  None, ['6', '7', '8', '9', '10'], '#BFDBFE'),
            ('Formal Stiletto Heels',     'footwear', 1100, 899, ['5', '6', '7', '8'],       '#BE185D'),
        ],
    },
    {
        'phone': '+919800000010',
        'name': 'Artisan Decor Studio',
        'category': 'decor',
        'description': 'Authentic Indian handicrafts — Dhokra, Madhubani, blue pottery, and more.',
        'address': '19, Nizampet Road, Hyderabad',
        'locality': 'Nizampet',
        'lat': 17.4992, 'lng': 78.3958,
        'logo': 'https://picsum.photos/seed/store-artisan/200/200',
        'banner': 'https://picsum.photos/seed/banner-artisan/800/300',
        'products': [
            ('Terracotta Pot Set',       'decor', 420,  None, [],  '#B45309'),
            ('Dhokra Art Bronze Figure', 'decor', 850,  None, [],  '#92400E'),
            ('Warli Tribal Painting',    'decor', 1200, 999, [],   '#1F2937'),
            ('Madhubani Art Frame',      'decor', 680,  None, [],  '#EC4899'),
            ('Pattachitra Fabric Panel', 'decor', 950,  None, [],  '#F59E0B'),
            ('Kalamkari Cushion Cover',  'decor', 380,  None, [],  '#D97706'),
            ('Blue Pottery Vase',        'decor', 760,  None, [],  '#2563EB'),
            ('Bidriware Jewellery Box',  'decor', 1400, None, [],  '#374151'),
            ('Brass Diya Set of 5',      'decor', 520,  None, [],  '#F59E0B'),
            ('Copper Water Bottle',      'decor', 650,  None, [],  '#D97706'),
        ],
    },
]

# Image seeds per product (sequential)
PRODUCT_IMG_SEEDS = [
    'kurta1', 'saree1', 'dupatta1', 'suit1', 'palazzo1', 'kurta2', 'dress1', 'kurti1', 'gown1', 'salwar1',
    'jhumka1', 'necklace1', 'bangles1', 'pearl1', 'kundan1', 'temple1', 'ring1', 'tikka1', 'ruby1', 'emerald1',
    'sneaker1', 'loafer1', 'chappal1', 'pump1', 'sport1', 'sandal1', 'oxford1', 'wedge1', 'mule1', 'boot1',
    'shelf1', 'cushion1', 'vase1', 'macrame1', 'lamp1', 'lantern1', 'basket1', 'candle1', 'frame1', 'runner1',
    'jacket1', 'hoodie1', 'jogger1', 'crop1', 'bomber1', 'leggings1', 'ethnic1', 'wrap1', 'bell1', 'shirt1',
    'georgette1', 'chiffon1', 'lehenga1', 'blouse1', 'zardosi1', 'net1', 'silk1', 'banarasi1', 'kalamkari1', 'block1',
    'kanjivaram1', 'mysore1', 'cotton1', 'tussar1', 'ikkat1', 'patola1', 'jamdani1', 'baluchari1', 'chanderi1', 'gadwal1',
    'diamond1', 'chain1', 'platinum1', 'rosegold1', 'whitegold1', 'sapphire1', 'rubyset1', 'emeraldring1', 'coral1', 'topaz1',
    'memory1', 'suede1', 'arch1', 'cork1', 'cushioned1', 'platform1', 'leathermule1', 'waterproof1', 'canvas1', 'stiletto1',
    'terracotta1', 'dhokra1', 'warli1', 'madhubani1', 'pattachitra1', 'kalamkari2', 'bluepottery1', 'bidriware1', 'brass1', 'copper1',
]


class Command(BaseCommand):
    help = 'Seed 10 test stores with 10 products each near Kukatpally, Hyderabad'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete previously seeded stores before re-seeding',
        )

    def handle(self, *args, **options):
        from apps.auth_app.models import User
        from apps.stores.models import Store, StoreHours
        from apps.products.models import Product, ProductVariant, ProductImage

        seed_phones = [s['phone'] for s in STORES]

        if options['clear']:
            deleted = User.objects.filter(phone_number__in=seed_phones).delete()
            self.stdout.write(self.style.WARNING(f'Cleared {deleted[0]} records.'))

        img_index = 0

        for store_data in STORES:
            phone = store_data['phone']

            # Create or get vendor user
            try:
                user = User.objects.get(phone_number=phone)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    phone_number=phone,
                    role='vendor',
                    full_name=store_data['name'] + ' Owner',
                )
                created = True
            if not created and hasattr(user, 'store'):
                self.stdout.write(f'  Skipping {store_data["name"]} — already exists')
                img_index += len(store_data['products'])
                continue

            # Create store
            store = Store.objects.create(
                owner=user,
                name=store_data['name'],
                description=store_data['description'],
                category=store_data['category'],
                phone=phone,
                address=store_data['address'],
                locality=store_data['locality'],
                location=Point(store_data['lng'], store_data['lat'], srid=4326),
                logo_url=store_data['logo'],
                banner_url=store_data['banner'],
                is_active=True,
                is_verified=True,
                is_open=True,
            )

            # Add store hours (Mon–Sun 10:00–21:00)
            for day in range(7):
                StoreHours.objects.create(
                    store=store,
                    day=day,
                    open_time=time(10, 0),
                    close_time=time(21, 0),
                    is_closed=(day == 6),  # Sunday closed
                )

            # Create products
            for prod_data in store_data['products']:
                name, category, base_price, sale_price, sizes, color = prod_data
                seed = PRODUCT_IMG_SEEDS[img_index % len(PRODUCT_IMG_SEEDS)]
                img_index += 1

                product = Product.objects.create(
                    store=store,
                    name=name,
                    description=f'{name} — available at {store.name} in {store.locality}.',
                    category=category,
                    status='active',
                    is_visible=True,
                    base_price=base_price,
                )

                # Primary product image
                ProductImage.objects.create(
                    product=product,
                    image_url=f'https://picsum.photos/seed/{seed}/400/500',
                    s3_key=f'test/{seed}.jpg',
                    is_primary=True,
                    order=0,
                )
                # Second image
                ProductImage.objects.create(
                    product=product,
                    image_url=f'https://picsum.photos/seed/{seed}-2/400/500',
                    s3_key=f'test/{seed}-2.jpg',
                    is_primary=False,
                    order=1,
                )

                # Variants
                if sizes:
                    for i, size in enumerate(sizes):
                        stock = 5 if i == 0 else (3 if i == 1 else (1 if i == 2 else 0))
                        variant_price = sale_price if sale_price else base_price
                        ProductVariant.objects.create(
                            product=product,
                            name=size,
                            sku=f'NK-{str(product.id)[:8]}-{size}',
                            price=variant_price,
                            stock_quantity=stock,
                        )
                else:
                    # No size variants — single variant
                    ProductVariant.objects.create(
                        product=product,
                        name='One Size',
                        sku=f'NK-{str(product.id)[:8]}-OS',
                        price=sale_price if sale_price else base_price,
                        stock_quantity=8,
                    )

            self.stdout.write(self.style.SUCCESS(
                f'  ✅  {store.name} ({store.locality}) — {len(store_data["products"])} products'
            ))

        self.stdout.write(self.style.SUCCESS('\n✅ Seeding complete! 10 stores × 10 products = 100 products'))
        self.stdout.write('   All stores open Mon–Sat 10:00–21:00, Sunday closed.')
        self.stdout.write('   Location: within 1.5km of Kukatpally (17.4948, 78.3996)')
