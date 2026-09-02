from django.db import migrations, models


# Non-atomic: each operation commits immediately — safe to re-run after any failure.
# All SQL is idempotent so repeated container restarts cannot corrupt state.

ADD_COLUMN_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stores' AND column_name = 'slug'
    ) THEN
        ALTER TABLE stores ADD COLUMN slug varchar(120) NULL;
    END IF;
END $$;
"""

BACKFILL_SQL = """
UPDATE stores
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

# Drop any stale partial indexes left by prior failed runs before re-creating.
CLEAN_STALE_SQL = """
DROP INDEX IF EXISTS stores_slug_c8d524d0_like;
DROP INDEX IF EXISTS stores_slug_c8d524d0;
ALTER TABLE stores DROP CONSTRAINT IF EXISTS stores_slug_key;
ALTER TABLE stores DROP CONSTRAINT IF EXISTS stores_store_slug_c8d524d0_uniq;
"""

ADD_UNIQUE_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'stores'::regclass AND contype = 'u'
          AND conname = 'stores_slug_key'
    ) THEN
        ALTER TABLE stores ADD CONSTRAINT stores_slug_key UNIQUE (slug);
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('stores', '0027_area14_store_review_flag'),
    ]

    operations = [
        # Steps 1-4: idempotent SQL handles all DB state
        migrations.RunSQL(ADD_COLUMN_SQL, migrations.RunSQL.noop),
        migrations.RunSQL(BACKFILL_SQL, migrations.RunSQL.noop),
        migrations.RunSQL(CLEAN_STALE_SQL, migrations.RunSQL.noop),
        migrations.RunSQL(ADD_UNIQUE_SQL, migrations.RunSQL.noop),
        # Step 5: update Django's migration state without touching the DB
        # (the SQL above already applied the correct schema)
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
            ],
        ),
    ]
