from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0016_store_women_owned'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='privacy_mode',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='store',
            name='holiday_mode',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='store',
            name='store_type',
            field=models.CharField(
                choices=[('product', 'Product Store'), ('service', 'Service Store'), ('home', 'Home Business')],
                default='product',
                max_length=10,
            ),
        ),
    ]
