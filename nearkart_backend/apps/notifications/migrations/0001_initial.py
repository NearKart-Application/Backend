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
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notification_type', models.CharField(
                    choices=[
                        ('new_message',             'New Message'),
                        ('reservation_created',     'Reservation Created'),
                        ('reservation_confirmed',   'Reservation Confirmed'),
                        ('reservation_cancelled',   'Reservation Cancelled'),
                        ('reservation_expired',     'Reservation Expired'),
                        ('new_follower',            'New Follower'),
                        ('new_review',              'New Review'),
                        ('store_opened',            'Store Opened'),
                        ('video_liked',             'Video Liked'),
                        ('video_ready',             'Video Ready'),
                        ('wallet_topup',            'Wallet Top-Up'),
                        ('subscription_expiring',   'Subscription Expiring'),
                        ('subscription_expired',    'Subscription Expired'),
                        ('group_added',             'Added to Group'),
                        ('group_removed',           'Removed from Group'),
                        ('group_product_shared',    'Product Shared in Group'),
                        ('group_product_finalized', 'Product Finalized in Group'),
                        ('group_admin_promoted',    'Promoted to Group Admin'),
                    ],
                    db_index=True,
                    max_length=30,
                )),
                ('title',  models.CharField(max_length=200)),
                ('body',   models.TextField()),
                ('data',   models.JSONField(blank=True, default=dict)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_read'], name='notif_recipient_read_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'created_at'], name='notif_recipient_time_idx'),
        ),
    ]
