"""
Usage:
  docker compose exec django python manage.py create_master_admin --phone +91XXXXXXXXXX --name "Your Name"

Creates or promotes a user to master_admin role.
Only one master admin can exist at a time.
Login via OTP as normal — no special password needed.
"""
from django.core.management.base import BaseCommand
from apps.auth_app.models import User, UserRole


class Command(BaseCommand):
    help = 'Create or promote a user to Master Admin'

    def add_arguments(self, parser):
        parser.add_argument('--phone', required=True, help='Phone number e.g. +919876543210')
        parser.add_argument('--name',  default='Master Admin', help='Full name')

    def handle(self, *args, **options):
        phone = options['phone'].strip()
        name  = options['name'].strip()

        existing_master = User.objects.filter(role=UserRole.MASTER_ADMIN).first()
        if existing_master and existing_master.phone_number != phone:
            self.stdout.write(self.style.ERROR(
                f'A master admin already exists: {existing_master.phone_number}. '
                'Delete them first or use the same phone number.'
            ))
            return

        if User.objects.filter(phone_number=phone).exists():
            user = User.objects.get(phone_number=phone)
            user.role          = UserRole.MASTER_ADMIN
            user.is_staff      = True
            user.is_superuser  = True
            user.full_name     = name
            user.save(update_fields=['role', 'is_staff', 'is_superuser', 'full_name', 'updated_at'])
            self.stdout.write(self.style.SUCCESS(
                f'✓ Existing user {phone} promoted to Master Admin (profile_id: {user.profile_id})'
            ))
        else:
            user = User.objects.create_user(
                phone_number=phone,
                role=UserRole.MASTER_ADMIN,
                full_name=name,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f'✓ Master Admin created: {phone} (profile_id: {user.profile_id})'
            ))

        self.stdout.write('Login via OTP in the app — use OTP 123456 in dev mode.')
