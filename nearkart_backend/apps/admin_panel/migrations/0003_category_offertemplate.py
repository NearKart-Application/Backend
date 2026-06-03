import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0002_activity_log'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('name',          models.CharField(max_length=100, unique=True)),
                ('slug',          models.SlugField(max_length=100, unique=True)),
                ('icon',          models.CharField(blank=True, max_length=10)),
                ('display_order', models.PositiveIntegerField(db_index=True, default=0)),
                ('is_active',     models.BooleanField(db_index=True, default=True)),
                ('created_by',    models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categories_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admin_categories', 'ordering': ['display_order', 'name']},
        ),
        migrations.CreateModel(
            name='OfferTemplate',
            fields=[
                ('id',                   models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',           models.DateTimeField(auto_now_add=True)),
                ('updated_at',           models.DateTimeField(auto_now=True)),
                ('name',                 models.CharField(max_length=200)),
                ('description_template', models.TextField(blank=True)),
                ('default_discount_pct', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('badge_text',           models.CharField(blank=True, max_length=20)),
                ('emoji',                models.CharField(blank=True, max_length=10)),
                ('image_url',            models.URLField(blank=True)),
                ('is_active',            models.BooleanField(db_index=True, default=True)),
                ('is_default',           models.BooleanField(db_index=True, default=False)),
                ('display_order',        models.PositiveIntegerField(db_index=True, default=0)),
                ('created_by',           models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='offer_templates_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'admin_offer_templates', 'ordering': ['display_order', 'name']},
        ),
    ]
