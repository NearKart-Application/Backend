import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('videos', '0005_video_is_pinned'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='videos.video')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='video_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'video_comments',
                'ordering': ['created_at'],
                'indexes': [
                    models.Index(fields=['video', 'created_at'], name='vidcomment_video_time_idx'),
                ],
            },
        ),
    ]
