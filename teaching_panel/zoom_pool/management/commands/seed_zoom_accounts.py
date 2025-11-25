from django.core.management.base import BaseCommand
from zoom_pool.models import ZoomAccount

TEST_ACCOUNTS = [
    {
        'email': 'zoom1@test.com',
        'api_key': 'test_key_1',
        'api_secret': 'test_secret_1',
        'max_concurrent_meetings': 2,
    },
    {
        'email': 'zoom2@test.com',
        'api_key': 'test_key_2',
        'api_secret': 'test_secret_2',
        'max_concurrent_meetings': 1,
    },
]

class Command(BaseCommand):
    help = 'Seed test Zoom accounts into the pool'

    def handle(self, *args, **options):
        created = 0
        for data in TEST_ACCOUNTS:
            obj, was_created = ZoomAccount.objects.get_or_create(
                email=data['email'],
                defaults=data
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seed complete. Created {created} new accounts. Total: {ZoomAccount.objects.count()}'))
