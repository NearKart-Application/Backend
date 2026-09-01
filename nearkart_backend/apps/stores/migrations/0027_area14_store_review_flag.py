from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('stores', '0026_store_photo_qa'),
    ]

    operations = [
        migrations.AddField(
            model_name='storereview',
            name='is_flagged',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='storereview',
            name='flag_reason',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
