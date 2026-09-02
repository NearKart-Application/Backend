from django.db import migrations, models


# Raw SQL backfill — handles both NULL and empty-string slugs.
# Appends the first 8 chars of UUID to guarantee uniqueness even with duplicate names.
BACKFILL_SQL = """
UPDATE stores_store
SET slug = LOWER(
    TRIM(BOTH '-' FROM
        REGEXP_REPLACE(
            REGEXP_REPLACE(COALESCE(NULLIF(TRIM(name), ''), 'store'), '[^a-zA-Z0-9]+', '-', 'g'),
            '-{2,}', '-', 'g'
        )
    )
) || '-' || LEFT(id::text, 8)
WHERE slug IS NULL OR slug = '';
"""


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
    ]

    operations = [
        # Step 1: add nullable, no constraint yet
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
        # Step 2: backfill — raw SQL so it runs inside the same transaction
        migrations.RunSQL(BACKFILL_SQL, migrations.RunSQL.noop),
        # Step 3: add unique constraint (null=True so PG allows multiple future NULLs)
        migrations.AlterField(
            model_name='store',
            name='slug',
            field=models.SlugField(
                blank=True,
                null=True,
                max_length=120,
                unique=True,
                help_text='Auto-generated URL slug for vendor mini-website (/s/<slug>).',
            ),
        ),
    ]
