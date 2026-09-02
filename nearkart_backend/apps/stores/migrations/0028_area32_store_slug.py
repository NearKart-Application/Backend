from django.db import migrations, models
from django.utils.text import slugify
import uuid


def generate_slugs(apps, schema_editor):
    Store = apps.get_model('stores', 'Store')
    used = set()
    for store in Store.objects.all().order_by('created_at'):
        base = slugify(store.name)[:80] or 'store'
        candidate = base
        counter = 1
        while candidate in used or Store.objects.filter(slug=candidate).exclude(pk=store.pk).exists():
            candidate = f'{base}-{counter}'
            counter += 1
        store.slug = candidate
        store.save(update_fields=['slug'])
        used.add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
    ]

    operations = [
        # Step 1: add nullable, no unique constraint yet
        migrations.AddField(
            model_name='store',
            name='slug',
            field=models.SlugField(
                blank=True,
                null=True,
                max_length=120,
                help_text='Auto-generated URL slug for vendor mini-website (/s/<slug>).',
            ),
        ),
        # Step 2: backfill slugs for all existing stores
        migrations.RunPython(generate_slugs, migrations.RunPython.noop),
        # Step 3: now safe to add unique constraint
        migrations.AlterField(
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
