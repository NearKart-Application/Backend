import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_productimage_s3_key_blank'),
        ('admin_panel', '0003_category_offertemplate'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='admin_panel.category',
            ),
        ),
    ]
