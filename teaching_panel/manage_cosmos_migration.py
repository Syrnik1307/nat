"""One-off script to migrate selected Django ORM data into Cosmos DB.

Usage (with COSMOS_DB_ENABLED=1 and emulator/service running):
    python manage.py shell -c "import manage_cosmos_migration as m; m.run()"

Keeps it simple: Lessons, ZoomAccounts, Attendance.
"""
from django.conf import settings
from django.utils import timezone
from schedule.models import Lesson, Attendance
from zoom_pool.models import ZoomAccount
from cosmos_repositories import lesson_repo, zoom_account_repo, attendance_repo
from cosmos_db import is_enabled


def run(dry_run=False):
    if not is_enabled():
        print("Cosmos disabled. Set COSMOS_DB_ENABLED=1 to proceed.")
        return
    total_lessons = Lesson.objects.count()
    total_accounts = ZoomAccount.objects.count()
    total_att = Attendance.objects.count()
    print(f"Found lessons={total_lessons} zoom_accounts={total_accounts} attendance={total_att}")

    migrated_l = migrated_a = migrated_att = 0
    if not dry_run:
        for obj in Lesson.objects.select_related('zoom_account').iterator():
            lesson_repo.upsert_from_model(obj)
            migrated_l += 1
        for acc in ZoomAccount.objects.iterator():
            zoom_account_repo.upsert_from_model(acc)
            migrated_a += 1
        for att in Attendance.objects.iterator():
            attendance_repo.upsert_from_model(att)
            migrated_att += 1
    print(f"Migration complete (dry_run={dry_run}). Lessons={migrated_l} ZoomAccounts={migrated_a} Attendance={migrated_att}")

if __name__ == '__main__':
    run(dry_run=False)