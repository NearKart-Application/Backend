import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0017_store_privacy_holiday_home_business'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerBlockedStore',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocked_stores', to=settings.AUTH_USER_MODEL)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocked_by_customers', to='stores.store')),
            ],
            options={
                'db_table': 'customer_blocked_stores',
                'ordering': ['-created_at'],
                'unique_together': {('customer', 'store')},
            },
        ),
    ]
