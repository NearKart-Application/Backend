from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_product_previous_price'),
        ('videos', '0003_videoproducttag'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='video_type',
            field=models.CharField(
                choices=[('store_promo', 'Store Promo'), ('product_demo', 'Product Demo')],
                db_index=True,
                default='store_promo',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='video',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='demo_videos',
                to='products.product',
            ),
        ),
    ]
