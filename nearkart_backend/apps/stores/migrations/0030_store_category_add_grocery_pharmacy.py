from django.db import migrations, models


class Migration(migrations.Migration):
    """Add grocery, pharmacy, books, sports to Store.category choices.

    Choices-only change (no DB schema change) so vendors can register these
    store types, which already map to existing inventory systems:
      grocery/pharmacy → Grocery/Perishable · books/sports → General.
    """

    dependencies = [
        ('stores', '0029_area33_store_gst_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='category',
            field=models.CharField(
                max_length=20,
                default='other',
                choices=[
                    ('fashion', 'Fashion'),
                    ('jewellery', 'Jewellery'),
                    ('footwear', 'Footwear'),
                    ('decor', 'Home Decor'),
                    ('furniture', 'Furniture'),
                    ('gifts', 'Gifts'),
                    ('beauty', 'Beauty'),
                    ('food', 'Food'),
                    ('electronics', 'Electronics'),
                    ('grocery', 'Grocery'),
                    ('pharmacy', 'Pharmacy'),
                    ('books', 'Books & Stationery'),
                    ('sports', 'Sports & Fitness'),
                    ('other', 'Other'),
                ],
            ),
        ),
    ]
