from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('stores', '0026_store_photo_qa'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyAnalyticsSnapshot',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('snapshot_date', models.DateField(db_index=True)),
                ('reservation_count', models.PositiveIntegerField(default=0)),
                ('completed_count', models.PositiveIntegerField(default=0)),
                ('revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('follower_count', models.PositiveIntegerField(default=0)),
                ('product_count', models.PositiveIntegerField(default=0)),
                ('video_view_count', models.PositiveIntegerField(default=0)),
                ('new_customer_count', models.PositiveIntegerField(default=0)),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='analytics_snapshots',
                    to='stores.store',
                )),
            ],
            options={
                'db_table': 'analytics_daily_snapshots',
                'ordering': ['-snapshot_date'],
                'unique_together': {('store', 'snapshot_date')},
            },
        ),
    ]
