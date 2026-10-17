from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='LocationMaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(db_index=True, max_length=100)),
                ('district', models.CharField(blank=True, db_index=True, default='', max_length=100)),
                ('city', models.CharField(blank=True, default='', max_length=100)),
            ],
            options={
                'db_table': 'location_master',
                'ordering': ['state', 'district', 'city'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='locationmaster',
            unique_together={('state', 'district', 'city')},
        ),
        migrations.AddIndex(
            model_name='locationmaster',
            index=models.Index(fields=['state', 'district'], name='loc_state_district_idx'),
        ),
    ]
