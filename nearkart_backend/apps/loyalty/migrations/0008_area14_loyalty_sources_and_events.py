from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ('loyalty', '0007_area13_transaction_expiry'),
        ('stores', '0026_store_photo_qa'),
    ]

    operations = [
        # Widen source field to accommodate new choices (source is a CharField — no AlterField needed
        # for just adding choices; choices are Python-side only; but we do need it for PointMultiplierEvent)
        migrations.CreateModel(
            name='PointMultiplierEvent',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200)),
                ('multiplier', models.DecimalField(decimal_places=2, default=2, max_digits=4)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('store', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='multiplier_events',
                    to='stores.store',
                    help_text='If null, applies platform-wide.',
                )),
            ],
            options={'db_table': 'loyalty_point_multiplier_events', 'ordering': ['-starts_at']},
        ),
    ]
