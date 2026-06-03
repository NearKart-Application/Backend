import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0006_store_owner_fk_multistore'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebsiteRequest',
            fields=[
                ('id',                models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
                ('status',            models.CharField(choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20)),
                ('domain_preference', models.CharField(blank=True, max_length=100)),
                ('notes',             models.TextField(blank=True)),
                ('admin_notes',       models.TextField(blank=True)),
                ('reviewed_at',       models.DateTimeField(blank=True, null=True)),
                ('store',             models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='website_request', to='stores.store')),
            ],
            options={'db_table': 'store_website_requests', 'ordering': ['-created_at']},
        ),
    ]
