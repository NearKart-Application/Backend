"""
Change Store.owner from OneToOneField to ForeignKey to support vendors
with multiple store locations.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0005_add_invoice_model'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='stores',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
