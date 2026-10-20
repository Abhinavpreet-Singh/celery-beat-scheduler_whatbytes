from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from scheduler.models import EmailPreference

EMAIL = 'abhinavpreet@whatbytes.com'

PEOPLE = [
    ('riya', 'Asia/Kolkata', 9),
    ('john', 'America/New_York', 8),
    ('mei', 'Asia/Tokyo', 10),
]


class Command(BaseCommand):
    help = 'Create sample users with email preferences'

    def handle(self, *args, **options):
        today = timezone.localtime().date()

        for username, zone, hour in PEOPLE:
            user, _ = User.objects.get_or_create(username=username, defaults={'email': EMAIL})
            EmailPreference.objects.update_or_create(
                user=user,
                defaults={
                    'email': EMAIL,
                    'timezone': zone,
                    'birthday': today,
                    'preferred_hour': hour,
                },
            )
            self.stdout.write(f'{username:6} {zone:18} birthday {today}')

        self.stdout.write(f'{EmailPreference.objects.count()} preferences, all mailing {EMAIL}')
