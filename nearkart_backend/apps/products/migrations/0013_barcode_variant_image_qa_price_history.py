from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_product_category_fk'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # #74 — barcode field on Product
        migrations.AddField(
            model_name='product',
            name='barcode',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        # #71 — variant FK on ProductImage
        migrations.AddField(
            model_name='productimage',
            name='variant',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='images',
                to='products.productvariant',
            ),
        ),
        # #75 — ProductQA
        migrations.CreateModel(
            name='ProductQA',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.TextField()),
                ('answer', models.TextField(blank=True)),
                ('answered_at', models.DateTimeField(blank=True, null=True)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='qa_entries',
                    to='products.product',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_questions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'product_qa', 'ordering': ['-created_at']},
        ),
        # #11 — ProductPriceHistory
        migrations.CreateModel(
            name='ProductPriceHistory',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='price_history',
                    to='products.product',
                )),
            ],
            options={'db_table': 'product_price_history', 'ordering': ['-created_at']},
        ),
    ]
