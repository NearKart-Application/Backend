import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0002_videosave'),
        ('products', '0002_add_subcategory_to_product'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoProductTag',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('x_pct', models.FloatField(default=0.5)),
                ('y_pct', models.FloatField(default=0.5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='video_tags',
                    to='products.product',
                )),
                ('video', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='product_tags',
                    to='videos.video',
                )),
            ],
            options={
                'ordering': ['created_at'],
                'unique_together': {('video', 'product')},
            },
        ),
    ]
