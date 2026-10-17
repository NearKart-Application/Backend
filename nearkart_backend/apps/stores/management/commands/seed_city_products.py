"""
Management command: seed_city_products
Creates 8 products per seeded store across all 5 cities.
Each product gets category-specific images, size variants where applicable.

Usage:
    python manage.py seed_city_products
    python manage.py seed_city_products --clear
    python manage.py seed_city_products --chunk 200
"""
import uuid
import random
from django.core.management.base import BaseCommand


# ── Category codes for product_code prefix ────────────────────────────────────
CAT_CODES = {
    'fashion':     'FA',
    'jewellery':   'JW',
    'footwear':    'FW',
    'decor':       'DC',
    'furniture':   'FN',
    'gifts':       'GF',
    'beauty':      'BT',
    'food':        'FD',
    'electronics': 'EL',
}

# ── Product catalog: 8 products per category ──────────────────────────────────
# Each entry: name, description, subcategory, base_price, sizes ([] = One Size), images
PRODUCT_CATALOG = {

    'fashion': [
        {
            'name': 'Cotton Printed Kurta',
            'description': 'Comfortable everyday cotton kurta with ethnic print detailing.',
            'subcategory': 'kurta',
            'base_price': 499,
            'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
            'images': [
                'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571513722275-4b41940f54b8?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Silk Saree',
            'description': 'Elegant handwoven silk saree with rich border — ideal for celebrations.',
            'subcategory': 'saree',
            'base_price': 1899,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1594938298603-c8148c4b58f8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1559526324-593bc073d938?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Embroidered Lehenga Choli',
            'description': 'Festive lehenga choli with intricate embroidery work.',
            'subcategory': 'lehenga',
            'base_price': 2499,
            'sizes': ['S', 'M', 'L', 'XL'],
            'images': [
                'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1594938298603-c8148c4b58f8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571513722275-4b41940f54b8?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Chiffon Dupatta',
            'description': 'Light chiffon dupatta with delicate embroidered border.',
            'subcategory': 'dupatta',
            'base_price': 349,
            'sizes': ['Free Size'],
            'images': [
                'https://images.unsplash.com/photo-1559526324-593bc073d938?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Straight-Cut Kurti',
            'description': 'Versatile straight-cut kurti suitable for office and casual wear.',
            'subcategory': 'kurti',
            'base_price': 399,
            'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
            'images': [
                'https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571513722275-4b41940f54b8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Floral Maxi Dress',
            'description': 'Breezy floral maxi dress — perfect for summer outings.',
            'subcategory': 'dress',
            'base_price': 799,
            'sizes': ['XS', 'S', 'M', 'L', 'XL'],
            'images': [
                'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1572804013427-4d7ca7268217?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Salwar Kameez Set',
            'description': 'Traditional salwar kameez set with matching dupatta.',
            'subcategory': 'salwar',
            'base_price': 899,
            'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
            'images': [
                'https://images.unsplash.com/photo-1594938298603-c8148c4b58f8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1583391733956-6c78276477e2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1559526324-593bc073d938?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Co-ord Set',
            'description': 'Trendy matching co-ord set — top and pants in one look.',
            'subcategory': 'co-ord set',
            'base_price': 1099,
            'sizes': ['XS', 'S', 'M', 'L', 'XL'],
            'images': [
                'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1572804013427-4d7ca7268217?w=400&h=500&fit=crop',
            ],
        },
    ],

    'jewellery': [
        {
            'name': 'Gold Plated Necklace',
            'description': 'Elegant gold plated necklace with intricate floral design.',
            'subcategory': 'necklace',
            'base_price': 1299,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Jhumka Earrings',
            'description': 'Traditional jhumka earrings with pearl and stone work.',
            'subcategory': 'earrings',
            'base_price': 649,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Bangles Set of 12',
            'description': 'Colourful glass bangles set — perfect for festive occasions.',
            'subcategory': 'bangles',
            'base_price': 299,
            'sizes': ['2.4', '2.6', '2.8'],
            'images': [
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Stone Ring',
            'description': 'Oxidized silver ring with semi-precious stone setting.',
            'subcategory': 'rings',
            'base_price': 349,
            'sizes': ['6', '7', '8', '9'],
            'images': [
                'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Pearl Bracelet',
            'description': 'Delicate freshwater pearl bracelet with gold clasp.',
            'subcategory': 'bracelet',
            'base_price': 799,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Pendant Necklace',
            'description': 'Minimalist gold pendant necklace for everyday elegance.',
            'subcategory': 'pendant',
            'base_price': 999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Maang Tikka',
            'description': 'Bridal maang tikka with kundan and pearl embellishments.',
            'subcategory': 'maang tikka',
            'base_price': 849,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Silver Anklet',
            'description': 'Traditional silver anklet with small bells — handcrafted.',
            'subcategory': 'anklet',
            'base_price': 449,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1601821765780-754fa98637c1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1573408301185-9519f94b02b8?w=400&h=500&fit=crop',
            ],
        },
    ],

    'footwear': [
        {
            'name': 'Canvas Sneakers',
            'description': 'Lightweight canvas sneakers for all-day comfort.',
            'subcategory': 'sneakers',
            'base_price': 699,
            'sizes': ['5', '6', '7', '8', '9', '10'],
            'images': [
                'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Flat Sandals',
            'description': 'Comfortable flat sandals with adjustable ankle strap.',
            'subcategory': 'sandals',
            'base_price': 499,
            'sizes': ['5', '6', '7', '8', '9'],
            'images': [
                'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Block Heel Pumps',
            'description': 'Elegant block heel pumps — comfort meets style.',
            'subcategory': 'heels',
            'base_price': 899,
            'sizes': ['5', '6', '7', '8'],
            'images': [
                'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Leather Loafers',
            'description': 'Classic leather loafers — ideal for office and casual wear.',
            'subcategory': 'loafers',
            'base_price': 1199,
            'sizes': ['6', '7', '8', '9', '10'],
            'images': [
                'https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Running Sports Shoes',
            'description': 'Breathable mesh running shoes with cushioned sole.',
            'subcategory': 'sports shoes',
            'base_price': 1499,
            'sizes': ['6', '7', '8', '9', '10', '11'],
            'images': [
                'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549298916-b41d501d3772?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Ballet Flats',
            'description': 'Classic ballet flats with soft cushioning — all-day comfort.',
            'subcategory': 'flats',
            'base_price': 599,
            'sizes': ['5', '6', '7', '8'],
            'images': [
                'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1560769629-975ec94e6a86?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Ankle Boots',
            'description': 'Stylish ankle boots with side zipper — perfect for winters.',
            'subcategory': 'boots',
            'base_price': 1999,
            'sizes': ['6', '7', '8', '9'],
            'images': [
                'https://images.unsplash.com/photo-1608256246200-86f82832fe02?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Kolhapuri Chappals',
            'description': 'Handcrafted Kolhapuri leather chappals — traditional and durable.',
            'subcategory': 'chappals',
            'base_price': 449,
            'sizes': ['5', '6', '7', '8', '9'],
            'images': [
                'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518894781321-630e638d0742?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1449505278894-297fdb3edbc1?w=400&h=500&fit=crop',
            ],
        },
    ],

    'decor': [
        {
            'name': 'Abstract Canvas Wall Art',
            'description': 'Vibrant abstract canvas painting to brighten up your walls.',
            'subcategory': 'wall art',
            'base_price': 799,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1532187643603-ba119ca4109e?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Ceramic Flower Vase',
            'description': 'Handpainted ceramic vase — perfect for fresh or dried flowers.',
            'subcategory': 'vase',
            'base_price': 449,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1490312278390-ab64016e0aa9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1612196808214-b7e239e5f6b3?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Boho Cushion Covers Set of 2',
            'description': 'Handwoven boho cushion covers with geometric patterns.',
            'subcategory': 'cushion covers',
            'base_price': 349,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567016432779-094069958ea5?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Bamboo Table Lamp',
            'description': 'Eco-friendly bamboo table lamp with warm LED bulb included.',
            'subcategory': 'lamp',
            'base_price': 1199,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1513506003901-1e6a35f6b8ae?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1565183928294-7063f23ce0f8?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Scented Soy Candle Set',
            'description': 'Set of 3 hand-poured soy wax candles in lavender, rose and sandalwood.',
            'subcategory': 'candles',
            'base_price': 399,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1602028915047-37269d1a73f7?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1603006905003-be475563bc59?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1612196808214-b7e239e5f6b3?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Collage Photo Frame Set',
            'description': 'Set of 6 matching photo frames for your cherished memories.',
            'subcategory': 'photo frame',
            'base_price': 499,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Floating Wall Shelf',
            'description': 'Solid wood floating wall shelf — sturdy and stylish storage.',
            'subcategory': 'wall shelf',
            'base_price': 699,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1532187643603-ba119ca4109e?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1513506003901-1e6a35f6b8ae?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Ceramic Planter',
            'description': 'Modern matte ceramic planter — suitable for indoor plants.',
            'subcategory': 'planter',
            'base_price': 349,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1490312278390-ab64016e0aa9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1612196808214-b7e239e5f6b3?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=500&fit=crop',
            ],
        },
    ],

    'furniture': [
        {
            'name': 'Ergonomic Study Chair',
            'description': 'Height-adjustable study chair with lumbar support.',
            'subcategory': 'chair',
            'base_price': 4999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Solid Wood Dining Table',
            'description': '4-seater solid sheesham wood dining table — built to last.',
            'subcategory': 'table',
            'base_price': 12999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': '3-Seater Fabric Sofa',
            'description': 'Comfortable 3-seater sofa with premium fabric upholstery.',
            'subcategory': 'sofa',
            'base_price': 18999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': '5-Shelf Bookcase',
            'description': 'Tall 5-shelf bookcase in natural wood finish.',
            'subcategory': 'bookshelf',
            'base_price': 6999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Storage Cabinet with Doors',
            'description': 'Multi-purpose storage cabinet with 2 doors and 3 shelves.',
            'subcategory': 'cabinet',
            'base_price': 8499,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Round Coffee Table',
            'description': 'Minimalist round coffee table with tempered glass top.',
            'subcategory': 'coffee table',
            'base_price': 5499,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1506439773649-6e0eb8cfb237?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': '6-Door Wardrobe',
            'description': 'Spacious 6-door wardrobe with mirror and multiple compartments.',
            'subcategory': 'wardrobe',
            'base_price': 22999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1556228453-efd6c1ff04f6?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1493663284031-b7e3aefcae8e?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Queen Size Bed Frame',
            'description': 'Solid wood queen size bed frame with storage drawers.',
            'subcategory': 'bed',
            'base_price': 16999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1505693314120-0d443867891c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=400&h=500&fit=crop',
            ],
        },
    ],

    'gifts': [
        {
            'name': 'Premium Gift Box',
            'description': 'Beautifully wrapped premium gift box — surprise your loved ones.',
            'subcategory': 'gift box',
            'base_price': 599,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Assorted Chocolate Box',
            'description': 'Handpicked assorted chocolates in a premium gift box.',
            'subcategory': 'chocolates',
            'base_price': 499,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Personalised Ceramic Mug',
            'description': 'Custom printed ceramic mug — add your own message or photo.',
            'subcategory': 'mug',
            'base_price': 299,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1512909006721-3d6018887383?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Luxury Scented Candle',
            'description': 'Premium long-burn scented candle in a glass jar.',
            'subcategory': 'candles',
            'base_price': 449,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1602028915047-37269d1a73f7?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Leather Keychain Set',
            'description': 'Set of 2 premium leather keychains — great as couple gifts.',
            'subcategory': 'keychain',
            'base_price': 249,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1512909006721-3d6018887383?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Festival Gift Hamper',
            'description': 'Curated festival hamper with dry fruits, chocolates and candles.',
            'subcategory': 'hamper',
            'base_price': 999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Greeting Cards Pack',
            'description': 'Pack of 10 handmade greeting cards for every occasion.',
            'subcategory': 'greeting cards',
            'base_price': 199,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1512909006721-3d6018887383?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1607344645866-009c320b63e0?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Personalized Photo Frame',
            'description': 'Custom engraved photo frame — perfect anniversary or birthday gift.',
            'subcategory': 'photo frame',
            'base_price': 399,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=400&h=500&fit=crop',
            ],
        },
    ],

    'beauty': [
        {
            'name': 'Matte Lipstick Set',
            'description': 'Set of 5 long-lasting matte lipsticks in trending shades.',
            'subcategory': 'lipstick',
            'base_price': 599,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Hydrating Face Moisturizer',
            'description': '24-hour hydrating moisturizer with SPF 15 — all skin types.',
            'subcategory': 'moisturizer',
            'base_price': 449,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Eye Shadow Palette',
            'description': '12-shade eye shadow palette with matte and shimmer finishes.',
            'subcategory': 'eye shadow',
            'base_price': 699,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Vitamin C Face Serum',
            'description': 'Brightening vitamin C serum for glowing, even-toned skin.',
            'subcategory': 'serum',
            'base_price': 799,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'SPF 50 Sunscreen',
            'description': 'Lightweight SPF 50 PA+++ sunscreen — no white cast.',
            'subcategory': 'sunscreen',
            'base_price': 349,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Dewy Foundation',
            'description': 'Medium-coverage dewy foundation with 16-hour wear.',
            'subcategory': 'foundation',
            'base_price': 649,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Volumizing Mascara',
            'description': 'Waterproof volumizing mascara for bold, clump-free lashes.',
            'subcategory': 'mascara',
            'base_price': 299,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1571875257727-256c39da42af?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1560707303-4e980ce876ad?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Smudge-Proof Kajal',
            'description': 'Intense black kajal pencil with smudge-proof formula.',
            'subcategory': 'kajal',
            'base_price': 149,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1487412912498-0447578fcca8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400&h=500&fit=crop',
            ],
        },
    ],

    'food': [
        {
            'name': 'Chicken Biryani',
            'description': 'Aromatic hyderabadi dum biryani made with premium basmati rice.',
            'subcategory': 'biryani',
            'base_price': 199,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1631515243349-e0cb75fb8d3a?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Veg Thali',
            'description': 'Full vegetarian thali with dal, sabzi, roti, rice and sweet.',
            'subcategory': 'thali',
            'base_price': 149,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Masala Dosa',
            'description': 'Crispy masala dosa served with sambar and 3 chutneys.',
            'subcategory': 'dosa',
            'base_price': 89,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1630851840628-fd9b2acdfbd4?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Gourmet Burger',
            'description': 'Juicy beef/veg burger with fresh veggies and house sauce.',
            'subcategory': 'burger',
            'base_price': 149,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1550547660-d9450f859349?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Margherita Pizza',
            'description': 'Classic margherita pizza with fresh mozzarella and basil.',
            'subcategory': 'pizza',
            'base_price': 199,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Club Sandwich',
            'description': 'Triple-decker club sandwich with chicken, cheese and fresh veggies.',
            'subcategory': 'sandwich',
            'base_price': 119,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Indian Sweet Box',
            'description': 'Assorted box of fresh gulab jamun, barfi and ladoo.',
            'subcategory': 'sweets',
            'base_price': 249,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Idli Sambar Set',
            'description': '4 soft idlis served with piping hot sambar and coconut chutney.',
            'subcategory': 'idli',
            'base_price': 69,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1630851840628-fd9b2acdfbd4?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400&h=500&fit=crop',
            ],
        },
    ],

    'electronics': [
        {
            'name': 'Wireless Earbuds',
            'description': 'True wireless earbuds with active noise cancellation and 30hr battery.',
            'subcategory': 'earbuds',
            'base_price': 1999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1627384113710-424c9181ebbb?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': '20000mAh Power Bank',
            'description': 'Fast-charging 20000mAh power bank with dual USB and Type-C ports.',
            'subcategory': 'power bank',
            'base_price': 1299,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Smart Watch',
            'description': 'Feature-rich smartwatch with health tracking, GPS and AMOLED display.',
            'subcategory': 'smart watch',
            'base_price': 3499,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Portable Bluetooth Speaker',
            'description': 'Waterproof portable speaker with 360° sound and 12hr battery.',
            'subcategory': 'speaker',
            'base_price': 1799,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': '7-Port USB Hub',
            'description': 'USB 3.0 7-port hub with individual power switches.',
            'subcategory': 'usb hub',
            'base_price': 799,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Adjustable Laptop Stand',
            'description': 'Aluminium adjustable laptop stand — ergonomic 6-angle setting.',
            'subcategory': 'laptop stand',
            'base_price': 999,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1498049794561-7780e7231661?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Tempered Glass Screen Protector',
            'description': '9H hardness tempered glass screen protector — crystal clear.',
            'subcategory': 'phone case',
            'base_price': 199,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1550009158-9ebf69173e03?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1535303311164-664fc9ec6532?w=400&h=500&fit=crop',
            ],
        },
        {
            'name': 'Wired Headphones',
            'description': 'Over-ear wired headphones with deep bass and noise isolation.',
            'subcategory': 'earbuds',
            'base_price': 899,
            'sizes': [],
            'images': [
                'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400&h=500&fit=crop',
                'https://images.unsplash.com/photo-1627384113710-424c9181ebbb?w=400&h=500&fit=crop',
            ],
        },
    ],
}


class Command(BaseCommand):
    help = 'Seed 8 products per store for all seeded city stores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all products from seeded stores before re-seeding',
        )
        parser.add_argument(
            '--chunk',
            type=int,
            default=200,
            help='Number of stores to process per batch (default: 200)',
        )

    def handle(self, *args, **options):
        from apps.stores.models import Store
        from apps.products.models import Product, ProductVariant, ProductImage

        chunk_size = options['chunk']

        # ── Clear ─────────────────────────────────────────────────────────────
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing seeded products...'))
            deleted = Product.objects.filter(store__phone__startswith='+917').delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted[0]} records.'))

        # ── Load seeded stores ────────────────────────────────────────────────
        store_qs = Store.objects.filter(
            phone__startswith='+917'
        ).only('id', 'category', 'phone').order_by('id')

        total_stores = store_qs.count()
        self.stdout.write(f'\nFound {total_stores} seeded stores. Creating 8 products each...\n')

        grand_products  = 0
        grand_variants  = 0
        grand_images    = 0
        processed       = 0

        # Process in chunks to keep memory manageable
        store_list = list(store_qs)
        for chunk_start in range(0, len(store_list), chunk_size):
            chunk = store_list[chunk_start:chunk_start + chunk_size]

            # Build (store, product_data) pairs for the chunk
            pairs = []
            for store in chunk:
                catalog = PRODUCT_CATALOG.get(store.category, PRODUCT_CATALOG['fashion'])
                for pd in catalog:
                    pairs.append((store, pd))

            # ── Bulk create Products ──────────────────────────────────────────
            cat_code = CAT_CODES
            product_objects = []
            for store, pd in pairs:
                product_objects.append(Product(
                    store=store,
                    product_code=f"NS{cat_code.get(store.category, 'OT')}{uuid.uuid4().hex[:12].upper()}",
                    name=pd['name'],
                    description=pd['description'],
                    category=store.category,
                    subcategory=pd['subcategory'],
                    status='active',
                    is_visible=True,
                    base_price=pd['base_price'],
                ))

            created_products = Product.objects.bulk_create(product_objects)
            # Guard: only process products that were actually saved to the DB
            saved_products = [(p, pair) for p, pair in zip(created_products, pairs) if p.pk is not None]

            # ── Bulk create Variants + Images ─────────────────────────────────
            variants = []
            images   = []

            for product, (store, pd) in saved_products:
                sizes = pd['sizes']
                if sizes:
                    for size in sizes:
                        variants.append(ProductVariant(
                            product=product,
                            name=size,
                            sku=f"{product.product_code}-{size.replace(' ', '')}",
                            price=pd['base_price'],
                            stock_quantity=random.randint(5, 30),
                        ))
                else:
                    variants.append(ProductVariant(
                        product=product,
                        name='One Size',
                        sku=f"{product.product_code}-OS",
                        price=pd['base_price'],
                        stock_quantity=random.randint(5, 30),
                    ))

                images.append(ProductImage(
                    product=product,
                    image_url=random.choice(pd['images']),
                    s3_key=f"seed/{product.product_code}.jpg",
                    is_primary=True,
                    order=0,
                ))

            ProductVariant.objects.bulk_create(variants)
            ProductImage.objects.bulk_create(images)

            grand_products += len(saved_products)
            grand_variants += len(variants)
            grand_images   += len(images)
            processed      += len(chunk)

            self.stdout.write(
                f'  Processed {processed}/{total_stores} stores — '
                f'{grand_products} products so far...'
            )

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f'\n✅  Done!'))
        self.stdout.write(f'   Products created : {grand_products}')
        self.stdout.write(f'   Variants created : {grand_variants}')
        self.stdout.write(f'   Images created   : {grand_images}')
        self.stdout.write('\n   To reset: python manage.py seed_city_products --clear')
