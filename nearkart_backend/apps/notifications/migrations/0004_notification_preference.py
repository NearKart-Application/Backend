import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0003_add_inventory_notification_types"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("chat",         models.BooleanField(default=True)),
                ("reservations", models.BooleanField(default=True)),
                ("offers",       models.BooleanField(default=True)),
                ("loyalty",      models.BooleanField(default=True)),
                ("wallet",       models.BooleanField(default=True)),
                ("new_product",  models.BooleanField(default=True)),
                ("general",      models.BooleanField(default=True)),
                ("push_enabled", models.BooleanField(default=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_pref",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"db_table": "notification_preferences"},
        ),
    ]
