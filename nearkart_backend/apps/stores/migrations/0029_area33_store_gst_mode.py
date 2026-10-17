from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0028_area32_store_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='gst_mode',
            field=models.CharField(
                choices=[
                    ('unregistered', 'Unregistered (No GST)'),
                    ('composition',  'Composition Scheme (1–5% flat turnover tax)'),
                    ('regular',      'Regular GST (18% + ITC eligible)'),
                ],
                default='unregistered',
                max_length=15,
                help_text='GST registration mode — controls invoice GST logic.',
            ),
        ),
    ]
