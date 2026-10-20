from django.db import migrations


def strip_baked_host(apps, schema_editor):
    """Convert host-baked media URLs to relative "/media/..." paths.

    Older uploads stored the request host (e.g. http://localhost/media/...,
    https://192.168.1.3:8000/media/...), which only loads from that exact host.
    Serializers now resolve relative media paths to an absolute URL per request,
    so strip the scheme+host here. External seed images (Unsplash/picsum) and any
    other non-media URLs don't contain "/media/" and are left untouched.
    """
    ProductImage = apps.get_model('products', 'ProductImage')
    marker = '/media/'
    for img in ProductImage.objects.all().iterator():
        url = img.image_url or ''
        if (url.startswith('http://') or url.startswith('https://')) and marker in url:
            relative = url[url.index(marker):]
            if relative != url:
                img.image_url = relative
                img.save(update_fields=['image_url'])


def noop(apps, schema_editor):
    # Irreversible by design — the original host is not recoverable and relative
    # URLs are the correct forward state.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0017_product_status_default_active'),
    ]

    operations = [
        migrations.RunPython(strip_baked_host, noop),
    ]
