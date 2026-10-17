from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0011_discount_codes'),
    ]

    operations = [
        migrations.CreateModel(
            name='BroadcastChannel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('auto_subscribe', models.BooleanField(default=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='broadcast_channels', to='stores.store')),
            ],
            options={'db_table': 'broadcast_channels', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='BroadcastPost',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.TextField()),
                ('image_url', models.URLField(blank=True)),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='stores.broadcastchannel')),
            ],
            options={'db_table': 'broadcast_posts', 'ordering': ['-created_at']},
        ),
    ]
