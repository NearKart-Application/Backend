import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0014_customeractivitylog'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialAccount',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(
                    choices=[('google', 'Google'), ('apple', 'Apple')],
                    db_index=True,
                    max_length=20,
                )),
                ('provider_uid', models.CharField(db_index=True, max_length=255)),
                ('extra_data', models.JSONField(blank=True, default=dict)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='social_accounts',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'auth_social_accounts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='socialaccount',
            constraint=models.UniqueConstraint(
                fields=['provider', 'provider_uid'],
                name='unique_provider_uid',
            ),
        ),
    ]
