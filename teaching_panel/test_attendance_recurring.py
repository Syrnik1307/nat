"""Тест генерации виртуальных уроков для журнала посещений"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import Group, RecurringLesson
from accounts.attendance_views import _generate_recurring_lessons_for_group

print("=" * 60)
print("Тестирование генерации виртуальных уроков")
print("=" * 60)

# Найдём все группы с регулярными уроками
groups_with_recurring = Group.objects.filter(recurring_lessons__isnull=False).distinct()

for g in groups_with_recurring[:3]:
    print(f"\n=== Группа {g.id}: {g.name} ===")
    
    rls = RecurringLesson.objects.filter(group=g)
    print(f"Регулярных уроков в БД: {rls.count()}")
    for rl in rls:
        print(f"  - '{rl.title}' день={rl.day_of_week} {rl.start_date} - {rl.end_date}")
    
    vls = _generate_recurring_lessons_for_group(g)
    print(f"\nВиртуальных уроков сгенерировано: {len(vls)}")
    for vl in vls[:10]:
        print(f"  - {vl['id']} | {vl['start_time'].strftime('%Y-%m-%d %H:%M')} | {vl['title']}")
    
    if len(vls) > 10:
        print(f"  ... и ещё {len(vls) - 10}")

print("\n" + "=" * 60)
print("Тест завершён")
