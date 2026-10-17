from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0003_category_offertemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='promobanner',
            name='target_city',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
