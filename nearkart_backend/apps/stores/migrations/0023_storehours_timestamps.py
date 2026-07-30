from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0022_add_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='storehours',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='storehours',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
