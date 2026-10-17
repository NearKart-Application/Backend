"""
Management command: seed_city_broadcasts
Creates one default BroadcastChannel per seeded store (phones starting '+917').
Stores that already have a channel are skipped (safe to re-run).
"""
from django.core.management.base import BaseCommand
from apps.stores.models import Store, BroadcastChannel


class Command(BaseCommand):
    help = 'Add a default BroadcastChannel to every seeded store (phones +917…)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete all broadcast channels from seeded stores first'
        )

    def handle(self, *args, **options):
        seeded_stores = Store.objects.filter(phone__startswith='+917')
        total = seeded_stores.count()

        if options['clear']:
            self.stdout.write('Clearing seeded broadcast channels…')
            deleted, _ = BroadcastChannel.objects.filter(store__in=seeded_stores).delete()
            self.stdout.write(f'Deleted {deleted} channels.')

        # Stores that already have at least one channel
        already_has = set(
            BroadcastChannel.objects.filter(store__in=seeded_stores)
            .values_list('store_id', flat=True)
        )

        to_create = []
        for store in seeded_stores.only('id', 'name', 'category'):
            if store.id in already_has:
                continue
            to_create.append(
                BroadcastChannel(
                    store          = store,
                    name           = f'{store.name} Updates',
                    description    = (
                        f'Get the latest products, offers, and news from {store.name}. '
                        f'We post new arrivals, exclusive deals, and store announcements here.'
                    ),
                    auto_subscribe = True,
                )
            )

        if not to_create:
            self.stdout.write(self.style.SUCCESS(
                f'All {total} seeded stores already have a broadcast channel. Nothing to do.'
            ))
            return

        BroadcastChannel.objects.bulk_create(to_create, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f'\n✅  Done! Created {len(to_create)} broadcast channels '
            f'({total - len(to_create)} stores already had one).'
        ))
        self.stdout.write('   To reset: python manage.py seed_city_broadcasts --clear')
