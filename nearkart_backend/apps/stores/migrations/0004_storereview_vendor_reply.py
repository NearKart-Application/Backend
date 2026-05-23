from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0003_add_store_offer'),
    ]

    operations = [
        migrations.AddField(
            model_name='storereview',
            name='vendor_reply',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='storereview',
            name='vendor_reply_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
