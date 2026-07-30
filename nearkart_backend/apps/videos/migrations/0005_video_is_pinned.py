from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0004_video_video_type_video_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='is_pinned',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
