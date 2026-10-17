import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PromoBanner',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('title',         models.CharField(max_length=100)),
                ('subtitle',      models.CharField(blank=True, max_length=200)),
                ('badge_text',    models.CharField(blank=True, max_length=20)),
                ('image_url',     models.URLField(blank=True)),
                ('link_type',     models.CharField(choices=[('store','Open Store'),('product','Open Product'),('category','Filter Category'),('external','External URL'),('none','No Action')], default='none', max_length=20)),
                ('link_value',    models.CharField(blank=True, max_length=500)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('is_active',     models.BooleanField(db_index=True, default=True)),
                ('starts_at',     models.DateTimeField(blank=True, null=True)),
                ('ends_at',       models.DateTimeField(blank=True, null=True)),
                ('is_paid',       models.BooleanField(default=False)),
                ('created_by',    models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='banners_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admin_promo_banners', 'ordering': ['display_order', '-created_at']},
        ),
    ]
