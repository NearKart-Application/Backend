from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0005_add_admin_profile'),
    ]

    operations = [
        # Expand admin_level max_length to fit 'district' (8 chars)
        migrations.AlterField(
            model_name='adminprofile',
            name='admin_level',
            field=models.CharField(
                choices=[
                    ('master',   'Master Admin'),
                    ('state',    'State Admin'),
                    ('district', 'District Admin'),
                    ('city',     'City Admin'),
                    ('area',     'Area / Village Admin'),
                ],
                default='district',
                max_length=10,
                help_text='Determines the scope of data this admin can see and modify.',
            ),
        ),
        # Add assigned_state
        migrations.AddField(
            model_name='adminprofile',
            name='assigned_state',
            field=models.CharField(
                blank=True, default='', max_length=150,
                help_text='Required for State/District/City/Area admins.',
            ),
        ),
        # Add assigned_area
        migrations.AddField(
            model_name='adminprofile',
            name='assigned_area',
            field=models.CharField(
                blank=True, default='', max_length=200,
                help_text='Required for Area/Village admins.',
            ),
        ),
        # Rename existing assigned_district help_text (no schema change needed, just alter)
        migrations.AlterField(
            model_name='adminprofile',
            name='assigned_district',
            field=models.CharField(
                blank=True, default='', max_length=200,
                help_text='Required for District/City/Area admins.',
            ),
        ),
        migrations.AlterField(
            model_name='adminprofile',
            name='assigned_city',
            field=models.CharField(
                blank=True, default='', max_length=200,
                help_text='Required for City/Area admins.',
            ),
        ),
    ]
