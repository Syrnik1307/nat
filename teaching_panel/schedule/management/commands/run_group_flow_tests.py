from django.core.management.base import BaseCommand
from schedule.tests.manual_group_flow import run as run_group_flow


class Command(BaseCommand):
    help = 'Execute automated coverage of GROUPS_AND_STUDENTS_TEST_PLAN backend scenarios'

    def handle(self, *args, **options):
        run_group_flow()
        self.stdout.write(self.style.SUCCESS('Group/invite flow tests completed'))
