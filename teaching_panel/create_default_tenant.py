#!/usr/bin/env python
"""
Скрипт миграции данных: создаёт дефолтный тенант и привязывает все существующие данные.

Запуск:
    python manage.py shell < create_default_tenant.py
    
    или

    python manage.py shell -c "exec(open('create_default_tenant.py').read())"
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.db import transaction
from tenants.models import Tenant, TenantMembership, TenantResourceLimits, TenantUsageStats


def create_default_tenant():
    """Создаёт дефолтный тенант и привязывает все существующие данные к нему."""
    
    print("=" * 60)
    print("МИГРАЦИЯ ДАННЫХ: Создание дефолтного тенанта")
    print("=" * 60)
    
    with transaction.atomic():
        # 1. Создаём или получаем дефолтный тенант
        tenant, created = Tenant.objects.get_or_create(
            slug='default',
            defaults={
                'name': 'Default Organization',
                'status': 'active',
            }
        )
        
        if created:
            print(f"✅ Создан тенант: {tenant.name} (slug={tenant.slug}, uuid={tenant.uuid})")
            
            # Создаёем ресурсные лимиты
            TenantResourceLimits.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'max_teachers': 50,
                    'max_students': 1000,
                    'max_groups': 100,
                    'max_courses': 50,
                    'max_lessons_per_month': 5000,
                    'max_homeworks': 2000,
                    'max_zoom_accounts': 20,
                    'max_concurrent_meetings': 50,
                }
            )
            print("✅ Ресурсные лимиты созданы (расширенные для миграции)")
            
            # Создадим статистику использования
            TenantUsageStats.objects.get_or_create(tenant=tenant)
            print("✅ Статистика использования создана")
        else:
            print(f"ℹ️  Тенант уже существует: {tenant.name}")
        
        # 2. Привязываем всех пользователей к тенанту
        from accounts.models import CustomUser
        users = CustomUser.objects.all()
        users_created = 0
        
        for user in users:
            role_map = {
                'admin': 'owner',
                'teacher': 'teacher',
                'student': 'student',
            }
            membership_role = role_map.get(user.role, 'student')
            
            # Первого admin делаем owner
            _, was_created = TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={'role': membership_role, 'is_active': True}
            )
            if was_created:
                users_created += 1
                
                # Первого admin назначаем owner тенанта
                if user.role == 'admin' and tenant.owner is None:
                    tenant.owner = user
                    tenant.save(update_fields=['owner'])
        
        print(f"✅ Создано {users_created} TenantMembership записей (из {users.count()} пользователей)")
        
        # 3. Привязываем все модели к тенанту
        from accounts.models import StatusBarMessage, Chat, SystemSettings
        from schedule.models import (
            ZoomAccount as ScheduleZoomAccount, Group, Lesson, 
            RecurringLesson, AuditLog as ScheduleAuditLog
        )
        from core.models import (
            Course, AuditLog as CoreAuditLog, 
            ProtectedContent, ContentAccessSession
        )
        from homework.models import Homework, StudentSubmission
        from analytics.models import ControlPoint
        from zoom_pool.models import ZoomAccount as PoolZoomAccount, ZoomPoolUsageMetrics
        from support.models import SupportTicket
        
        models_to_update = [
            ('StatusBarMessage', StatusBarMessage),
            ('Chat', Chat),
            ('SystemSettings', SystemSettings),
            ('Schedule.ZoomAccount', ScheduleZoomAccount),
            ('Group', Group),
            ('Lesson', Lesson),
            ('RecurringLesson', RecurringLesson),
            ('Schedule.AuditLog', ScheduleAuditLog),
            ('Course', Course),
            ('Core.AuditLog', CoreAuditLog),
            ('ProtectedContent', ProtectedContent),
            ('ContentAccessSession', ContentAccessSession),
            ('Homework', Homework),
            ('StudentSubmission', StudentSubmission),
            ('ControlPoint', ControlPoint),
            ('ZoomPool.ZoomAccount', PoolZoomAccount),
            ('ZoomPoolUsageMetrics', ZoomPoolUsageMetrics),
            ('SupportTicket', SupportTicket),
        ]
        
        for name, model in models_to_update:
            count = model.objects.filter(tenant__isnull=True).update(tenant=tenant)
            if count > 0:
                print(f"  📦 {name}: {count} записей привязано к тенанту")
            else:
                # Проверим, есть ли вообще записи
                total = model.objects.count()
                if total > 0:
                    print(f"  ✓ {name}: все {total} записей уже привязаны")
                else:
                    print(f"  - {name}: нет записей")
        
        # 4. Пересчитываем статистику использования
        usage, _ = TenantUsageStats.objects.get_or_create(tenant=tenant)
        usage.recalculate()
        print(f"\n✅ Статистика пересчитана:")
        print(f"   Учителей: {usage.current_teachers}")
        print(f"   Учеников: {usage.current_students}")
        print(f"   Групп: {usage.current_groups}")
        print(f"   Курсов: {usage.current_courses}")
    
    print("\n" + "=" * 60)
    print("МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
    print(f"Тенант UUID: {tenant.uuid}")
    print("=" * 60)
    
    return tenant


if __name__ == '__main__':
    create_default_tenant()
else:
    # Running via manage.py shell
    create_default_tenant()
