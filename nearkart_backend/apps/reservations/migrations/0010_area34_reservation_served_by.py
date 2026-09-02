from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('reservations', '0009_reservation_payment_method'),
        ('stores', '0029_area33_store_gst_mode'),
    ]
    operations = [
        migrations.AddField(
            model_name='reservation',
            name='served_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='served_reservations',
                to='stores.staffmember',
                help_text='Staff member who attended the customer at pickup.',
            ),
        ),
    ]
