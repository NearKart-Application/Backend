import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0012_add_location_state_district'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserLoginLog',
            fields=[
                ('id',             models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at',     models.DateTimeField(auto_now_add=True)),
                ('updated_at',     models.DateTimeField(auto_now=True)),
                ('phone',          models.CharField(db_index=True, max_length=20)),
                ('role',           models.CharField(blank=True, max_length=20)),
                ('success',        models.BooleanField(default=True, db_index=True)),
                ('failure_reason', models.CharField(blank=True, max_length=50)),
                ('ip_address',     models.GenericIPAddressField(blank=True, null=True)),
                ('city',           models.CharField(blank=True, max_length=150)),
                ('device_type',    models.CharField(choices=[('mobile','Mobile'),('tablet','Tablet'),('desktop','Desktop'),('unknown','Unknown')], default='unknown', max_length=10)),
                ('device_name',    models.CharField(blank=True, max_length=200)),
                ('os',             models.CharField(blank=True, max_length=50)),
                ('os_version',     models.CharField(blank=True, max_length=30)),
                ('browser',        models.CharField(blank=True, max_length=100)),
                ('app_version',    models.CharField(blank=True, max_length=30)),
                ('user_agent',     models.TextField(blank=True)),
                ('user',           models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                    related_name='login_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'auth_login_logs', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='userloginlog',
            index=models.Index(fields=['phone', 'created_at'], name='login_log_phone_idx'),
        ),
        migrations.AddIndex(
            model_name='userloginlog',
            index=models.Index(fields=['success', 'created_at'], name='login_log_success_idx'),
        ),
    ]
