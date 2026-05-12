"""
Management command to create a superadmin user.

Usage:
    python manage.py create_superadmin
    python manage.py create_superadmin --username admin --email admin@example.com --password secret
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superadmin user for the MindConnect platform'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email', default='admin@mindconnect.com')
        parser.add_argument('--password', default='Admin@123!')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Superadmin "{username}" already exists. Skipping.'
            ))
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        user.is_online = False
        user.email_verified = True
        user.save(update_fields=['is_online', 'email_verified'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Superadmin created successfully!\n'
            f'   Username : {username}\n'
            f'   Email    : {email}\n'
            f'   Password : {password}\n'
            f'   Admin URL: http://localhost:8000/admin/\n'
        ))
