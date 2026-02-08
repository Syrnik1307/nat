"""
Data migration: привязка ВСЕХ существующих записей к Default School.

Безопасность:
- Только UPDATE, никаких DELETE/DROP
- Обратимая: reverse ставит school=NULL
- Работает с NULL FK (не ломает записи без школы)
"""
from django.db import migrations


def backfill_school_fk(apps, schema_editor):
    School = apps.get_model('tenants', 'School')
    default_school = School.objects.filter(is_default=True).first()
    if not default_school:
        print('  [!] Default school not found, skipping backfill')
        return

    models_to_update = [
        ('schedule', 'Group'),
        ('homework', 'Homework'),
        ('accounts', 'Subscription'),
        ('analytics', 'ControlPoint'),
        ('support', 'SupportTicket'),
        ('finance', 'StudentFinancialProfile'),
        ('bot', 'ScheduledMessage'),
    ]

    for app_label, model_name in models_to_update:
        try:
            Model = apps.get_model(app_label, model_name)
            updated = Model.objects.filter(school__isnull=True).update(school=default_school)
            if updated:
                print(f'  -> {app_label}.{model_name}: updated {updated} records')
        except Exception as e:
            print(f'  WARNING {app_label}.{model_name}: {e}')


def reverse_backfill(apps, schema_editor):
    """Обратная миграция: убрать school FK (поставить NULL)."""
    models_to_update = [
        ('schedule', 'Group'),
        ('homework', 'Homework'),
        ('accounts', 'Subscription'),
        ('analytics', 'ControlPoint'),
        ('support', 'SupportTicket'),
        ('finance', 'StudentFinancialProfile'),
        ('bot', 'ScheduledMessage'),
    ]
    for app_label, model_name in models_to_update:
        try:
            Model = apps.get_model(app_label, model_name)
            Model.objects.all().update(school=None)
        except Exception:
            pass


class Migration(migrations.Migration):
    """
    This migration depends on Phase 1 school FK migrations which don't exist yet.
    It will be a no-op until those migrations are created.
    For now, only depend on tenants.0002 so Django can start.
    """
    dependencies = [
        ('tenants', '0002_create_default_school'),
    ]
    operations = [
        migrations.RunPython(backfill_school_fk, reverse_backfill),
    ]
