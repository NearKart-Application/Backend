from django.db import migrations, models
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    Store = apps.get_model('stores', 'Store')
    used = set()
    for store in Store.objects.filter(slug__isnull=True).order_by('created_at'):
        base = slugify(store.name or '')[:80] or f'store-{str(store.id)[:8]}'
        candidate = base
        counter = 1
        while candidate in used:
            candidate = f'{base}-{counter}'
            counter += 1
        # Use .update() — reliable in migrations, bypasses save() hooks
        Store.objects.filter(pk=store.pk).update(slug=candidate)
        used.add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
    ]

    operations = [
        # Step 1: add as nullable so existing rows are NULL (not empty string)
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
        # Step 2: backfill — every row gets a unique slug via .update() (no save() hooks)
        migrations.RunPython(generate_slugs, migrations.RunPython.noop),
        # Step 3: tighten to unique; default='' so new rows without a slug get empty str,
        #         but the save() on Store.save() always sets one before insert.
        migrations.AlterField(
            model_name='store',
            name='slug',
            field=models.SlugField(
                blank=True,
                null=True,          # keep nullable — unique index allows multiple NULLs in PG
                max_length=120,
                unique=True,
                help_text='Auto-generated URL slug for vendor mini-website (/s/<slug>).',
            ),
        ),
    ]
