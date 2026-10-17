from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0025_vendoractionlog'),
        ('auth_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StorePhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image_url', models.URLField()),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='stores.store')),
            ],
            options={'db_table': 'store_photos', 'ordering': ['order', 'created_at']},
        ),
        migrations.CreateModel(
            name='StoreQuestion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question', models.TextField()),
                ('answer', models.TextField(blank=True)),
                ('answered_at', models.DateTimeField(blank=True, null=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='stores.store')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_questions', to='auth_app.user')),
            ],
            options={'db_table': 'store_questions', 'ordering': ['-created_at']},
        ),
    ]
