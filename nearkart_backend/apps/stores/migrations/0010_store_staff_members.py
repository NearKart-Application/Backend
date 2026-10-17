from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0009_invoice_customer_ns_code'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffMember',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(
                    choices=[('manager', 'Manager'), ('staff', 'Staff')],
                    default='staff', max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('invited_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invited_staff',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('store', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='staff_members',
                    to='stores.store',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='staff_roles',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'store_staff_members',
                'ordering': ['created_at'],
                'unique_together': {('store', 'user')},
            },
        ),
    ]
