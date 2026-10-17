import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0001_promo_banner'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminActivityLog',
            fields=[
                ('id',           models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('action',       models.CharField(max_length=50)),
                ('target_type',  models.CharField(blank=True, max_length=50)),
                ('target_id',    models.CharField(blank=True, max_length=100)),
                ('target_label', models.CharField(blank=True, max_length=200)),
                ('detail',       models.CharField(blank=True, max_length=500)),
                ('admin',        models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='admin_actions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'admin_activity_log', 'ordering': ['-created_at']},
        ),
    ]
