from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0008_store_documents'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='customer_ns_code',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
