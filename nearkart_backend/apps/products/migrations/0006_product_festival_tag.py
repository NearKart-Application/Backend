from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_alter_stockmovementlog_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='festival_tag',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
