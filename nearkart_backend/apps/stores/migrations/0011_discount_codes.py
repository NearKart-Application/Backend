import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0010_store_staff_members'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscountCode',
            fields=[
                ('id',               models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
                ('updated_at',       models.DateTimeField(auto_now=True)),
                ('code',             models.CharField(max_length=20)),
                ('description',      models.CharField(blank=True, max_length=100)),
                ('discount_type',    models.CharField(choices=[('percent', 'Percent off'), ('flat', 'Flat amount off')], default='percent', max_length=10)),
                ('value',            models.DecimalField(decimal_places=2, max_digits=8)),
                ('min_order_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('max_uses',         models.PositiveIntegerField(blank=True, null=True)),
                ('uses_count',       models.PositiveIntegerField(default=0)),
                ('valid_from',       models.DateField(blank=True, null=True)),
                ('valid_till',       models.DateField(blank=True, null=True)),
                ('is_active',        models.BooleanField(db_index=True, default=True)),
                ('store',            models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discount_codes', to='stores.store')),
                ('created_by',       models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_discount_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'discount_codes', 'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='discountcode',
            constraint=models.UniqueConstraint(fields=['store', 'code'], name='unique_store_code'),
        ),
    ]
