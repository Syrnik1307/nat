"""
Management command to check FRONTEND_URL configuration
"""
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Check FRONTEND_URL configuration'

    def handle(self, *args, **options):
        self.stdout.write(f'FRONTEND_URL: {settings.FRONTEND_URL}')
        self.stdout.write(self.style.SUCCESS('✓ Check complete'))
