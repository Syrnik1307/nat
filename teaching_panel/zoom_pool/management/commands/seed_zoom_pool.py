from django.core.management.base import BaseCommand
from zoom_pool.models import ZoomAccount


SAMPLE_ACCOUNTS = [
    {
        'email': 'zoom1@test.com',
        'api_key': 'test_key_1',
        'api_secret': 'test_secret_1',
        'zoom_user_id': 'user_1',
        'max_concurrent_meetings': 2,
    },
    {
        'email': 'zoom2@test.com',
        'api_key': 'test_key_2',
        'api_secret': 'test_secret_2',
        'zoom_user_id': 'user_2',
        'max_concurrent_meetings': 1,
    },
]


class Command(BaseCommand):
    help = "Seeds sample Zoom pool accounts for development"

    def handle(self, *args, **options):
        created = 0
        for acc in SAMPLE_ACCOUNTS:
            obj, was_created = ZoomAccount.objects.get_or_create(
                email=acc['email'],
                defaults=acc
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seed complete. Created {created} accounts."))