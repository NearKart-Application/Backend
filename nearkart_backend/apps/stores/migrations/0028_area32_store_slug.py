from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=120,
                unique=True,
                help_text='Auto-generated URL slug for vendor mini-website (/s/<slug>).',
            ),
        ),
    ]
