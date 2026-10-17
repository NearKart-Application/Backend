from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0007_website_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='license_url',
            field=models.URLField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='store',
            name='gst_url',
            field=models.URLField(blank=True, default=''),
            preserve_default=False,
        ),
    ]
