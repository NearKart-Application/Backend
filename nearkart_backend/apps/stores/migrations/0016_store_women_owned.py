from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0015_store_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='is_women_owned',
            field=models.BooleanField(default=False),
        ),
    ]
