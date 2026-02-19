#!/usr/bin/env python3
"""
Скрипт миграции School → Tenant на проде.
Запускать из /var/www/teaching_panel/teaching_panel/

Обновляет Python-файлы:
1. Модели: school FK → tenant FK
2. Views/mixins: request.school → request.tenant
3. Imports: School → Tenant, SchoolMembership → TenantMembership
"""
import re
import os
import shutil
from datetime import datetime

BASE = '/var/www/teaching_panel/teaching_panel'
BACKUP_DIR = f'/var/www/teaching_panel/backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'


def backup_file(filepath):
    """Создать бэкап файла."""
    rel = os.path.relpath(filepath, BASE)
    dst = os.path.join(BACKUP_DIR, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(filepath, dst)
    print(f'  [backup] {rel}')


def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def replace_in_file(filepath, replacements):
    """
    replacements: list of (old, new) tuples
    """
    content = read_file(filepath)
    backup_file(filepath)
    
    for old, new in replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f'  [{os.path.relpath(filepath, BASE)}] "{old}" → "{new}" ({count}x)')
        else:
            print(f'  [{os.path.relpath(filepath, BASE)}] SKIP: "{old}" not found')
    
    write_file(filepath, content)


def migrate_model_fk(filepath):
    """
    Меняем:
      school = models.ForeignKey(
          'tenants.School',
    на:
      tenant = models.ForeignKey(
          'tenants.Tenant',
    """
    content = read_file(filepath)
    backup_file(filepath)
    
    # Паттерн для FK определения
    pattern = r"school\s*=\s*models\.ForeignKey\(\s*\n\s*'tenants\.School'"
    replacement = "tenant = models.ForeignKey(\n        'tenants.Tenant'"
    
    new_content, count = re.subn(pattern, replacement, content)
    if count > 0:
        print(f'  [{os.path.relpath(filepath, BASE)}] FK school→tenant ({count}x)')
    
    # Также меняем related_name если есть school_*
    new_content = new_content.replace(
        "related_name='school_", 
        "related_name='tenant_"
    )
    
    write_file(filepath, new_content)


def migrate_core_tenant_mixins():
    """Обновить core/tenant_mixins.py"""
    filepath = os.path.join(BASE, 'core', 'tenant_mixins.py')
    content = read_file(filepath)
    backup_file(filepath)
    
    new_content = '''"""
Tenant-Ready Mixins для ViewSets.

Multi-tenant изоляция данных по тенантам (организациям).

Как использовать:
    class GroupViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
        queryset = Group.objects.all()
        ...

TenantMiddleware определяет тенант по поддомену и кладёт в request.tenant.
Этот миксин автоматически фильтрует queryset по тенанту.

Feature flag: TENANT_ISOLATION_ENABLED (settings.py)
  False → pass-through, ничего не фильтрует
  True  → полная изоляция по tenant
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_current_tenant():
    """Безопасный импорт для избежания circular imports."""
    try:
        from tenants.middleware import get_current_tenant
        return get_current_tenant()
    except ImportError:
        return None


class TenantViewSetMixin:
    """
    Миксин для ViewSets с tenant-изоляцией.

    Автоматически:
    - Фильтрует queryset по tenant (когда TENANT_ISOLATION_ENABLED=True)
    - Привязывает tenant при создании объектов
    - Fallback на всех учителей тенанта для моделей без прямого tenant FK
    - Superuser видит всё (нет фильтрации)
    """

    def get_queryset(self):
        qs = super().get_queryset()

        if not getattr(settings, 'TENANT_ISOLATION_ENABLED', False):
            return qs

        # Superuser видит всё
        if hasattr(self, 'request') and self.request.user.is_superuser:
            return qs

        tenant = getattr(self.request, 'tenant', None) or _get_current_tenant()
        if not tenant:
            return qs

        if hasattr(qs.model, 'tenant'):
            # Модели с прямым tenant FK (Group, Homework, Subscription, etc)
            qs = qs.filter(tenant=tenant)
        elif hasattr(qs.model, 'teacher'):
            # Модели без tenant FK, привязанные к учителю
            from tenants.models import TenantMembership
            teacher_ids = TenantMembership.objects.filter(
                tenant=tenant,
                role__in=['owner', 'admin', 'teacher'],
                is_active=True,
            ).values_list('user_id', flat=True)
            qs = qs.filter(teacher_id__in=teacher_ids)

        return qs

    def perform_create(self, serializer):
        if getattr(settings, 'TENANT_ISOLATION_ENABLED', False):
            tenant = getattr(self.request, 'tenant', None) or _get_current_tenant()
            if tenant and hasattr(serializer.Meta.model, 'tenant'):
                serializer.save(tenant=tenant)
                return

        super().perform_create(serializer)


class TenantSerializerMixin:
    """
    Миксин для Serializers — скрывает tenant поле от API.

    Tenant определяется middleware, не клиентом.
    tenant поле read_only, устанавливается автоматически из request.
    """
    pass
'''
    write_file(filepath, new_content)
    print(f'  [core/tenant_mixins.py] ПОЛНОСТЬЮ ПЕРЕПИСАН')


def migrate_accounts_api_views():
    """accounts/api_views.py — request.school → request.tenant, SchoolMembership → TenantMembership"""
    filepath = os.path.join(BASE, 'accounts', 'api_views.py')
    replace_in_file(filepath, [
        ("request, 'school'", "request, 'tenant'"),
        ("request.school", "request.tenant"),
        ("from tenants.models import SchoolMembership", "from tenants.models import TenantMembership"),
        ("SchoolMembership.objects", "TenantMembership.objects"),
        (".school =", ".tenant ="),
        (".school_id", ".tenant_id"),
    ])


def migrate_accounts_jwt_views():
    """accounts/jwt_views.py — registration with school"""
    filepath = os.path.join(BASE, 'accounts', 'jwt_views.py')
    replace_in_file(filepath, [
        # getattr
        ("getattr(request, 'school', None)", "getattr(request, 'tenant', None)"),
        # Imports
        ("from tenants.models import SchoolMembership", "from tenants.models import TenantMembership"),
        # ORM calls
        ("SchoolMembership.objects", "TenantMembership.objects"),
        # FK kwargs
        ("school=school", "tenant=tenant"),
        # Variable assignment
        ("school = getattr", "tenant = getattr"),
        # Conditionals
        ("if school:", "if tenant:"),
        ("if school and", "if tenant and"),
        # Field access
        ("school.slug", "tenant.slug"),
        ("school.name", "tenant.name"),
        # Log messages
        ("SchoolMembership created", "TenantMembership created"),
        ("f'School ", "f'Tenant "),
        ("'School ", "'Tenant "),
    ])


def migrate_accounts_payments_service():
    """accounts/payments_service.py — complex case with metadata keys.
    
    ВАЖНО: 'school_id' как ключ метаданных платёжных систем ОСТАВЛЯЕМ
    для обратной совместимости с вебхуками YooKassa/TBank.
    """
    filepath = os.path.join(BASE, 'accounts', 'payments_service.py')
    content = read_file(filepath)
    backup_file(filepath)
    
    # Imports
    content = content.replace(
        "from tenants.models import School",
        "from tenants.models import Tenant"
    )
    
    # Docstrings/комментарии
    content = content.replace("school: School instance", "tenant: Tenant instance")
    content = content.replace("school: School", "tenant: Tenant")
    content = content.replace("(multi-tenant)", "(multi-tenant)")
    
    # _meta_school_id → _meta_tenant_id (внутренняя переменная)
    content = content.replace("_meta_school_id", "_meta_tenant_id")
    
    # school.pk, school.id → tenant.pk, tenant.id  
    content = content.replace("str(school.pk)", "str(tenant.pk)")
    content = content.replace("str(school.id)", "str(tenant.id)")
    
    # school else '' → tenant else ''
    content = content.replace("school else ''", "tenant else ''")
    content = content.replace("school else {}", "tenant else {}")
    
    # Локальные переменные
    content = content.replace("_school_to_bind", "_tenant_to_bind")
    content = content.replace("School.objects.get", "Tenant.objects.get")
    content = content.replace('f"[WEBHOOK] School ', 'f"[WEBHOOK] Tenant ')
    content = content.replace("'School ", "'Tenant ")
    
    # sub.school = → sub.tenant =
    content = content.replace("sub.school =", "sub.tenant =")
    content = content.replace("sub.school_id", "sub.tenant_id")
    content = content.replace("not sub.school_id", "not sub.tenant_id")
    
    # Параметр/переменная school (но НЕ в строковых литералах 'school_id')
    # Аккуратная замена: def func(..., school, ...) → def func(..., tenant, ...)
    # и school = ... → tenant = ...
    content = content.replace("if school else", "if tenant else")
    content = content.replace("if school:", "if tenant:")
    content = content.replace("school =", "tenant =")
    
    write_file(filepath, content)
    print(f'  [accounts/payments_service.py] ОБНОВЛЁН (метаданные school_id оставлены для совместимости)')


def migrate_accounts_subscriptions_views():
    """accounts/subscriptions_views.py"""
    filepath = os.path.join(BASE, 'accounts', 'subscriptions_views.py')
    replace_in_file(filepath, [
        ("request, 'school'", "request, 'tenant'"),
        ("request.school", "request.tenant"),
        ("school =", "tenant ="),
    ])


def migrate_settings():
    """teaching_panel/settings.py — just comments, minor"""
    filepath = os.path.join(BASE, 'teaching_panel', 'settings.py')
    content = read_file(filepath)
    backup_file(filepath)
    # Обновляем комментарии 
    content = content.replace(
        "# Определение школы по поддомену",
        "# Определение тенанта по поддомену"
    )
    content = content.replace(
        "Определение школы по поддомену",
        "Определение тенанта по поддомену"
    )
    write_file(filepath, content)
    print(f'  [settings.py] комментарии обновлены')


def main():
    print(f'╔══════════════════════════════════════╗')
    print(f'║  School → Tenant: миграция кода      ║')
    print(f'╚══════════════════════════════════════╝')
    print(f'Working dir: {BASE}')
    print(f'Backup: {BACKUP_DIR}')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print()
    
    # 1. Модели с FK
    print('=== 1. Миграция FK в моделях ===')
    model_files = [
        'accounts/models.py',
        'analytics/models.py', 
        'bot/models.py',
        'finance/models.py',
        'homework/models.py',
        'schedule/models.py',
        'support/models.py',
    ]
    for mf in model_files:
        migrate_model_fk(os.path.join(BASE, mf))
    
    # 2. core/tenant_mixins.py
    print('\n=== 2. core/tenant_mixins.py ===')
    migrate_core_tenant_mixins()
    
    # 3. accounts/api_views.py
    print('\n=== 3. accounts/api_views.py ===')
    migrate_accounts_api_views()
    
    # 4. accounts/jwt_views.py  
    print('\n=== 4. accounts/jwt_views.py ===')
    migrate_accounts_jwt_views()
    
    # 5. accounts/payments_service.py
    print('\n=== 5. accounts/payments_service.py ===')
    migrate_accounts_payments_service()
    
    # 6. accounts/subscriptions_views.py
    print('\n=== 6. accounts/subscriptions_views.py ===')
    migrate_accounts_subscriptions_views()
    
    # 7. settings.py
    print('\n=== 7. settings.py ===')
    migrate_settings()
    
    print('\n╔══════════════════════════════════════╗')
    print('║  Миграция кода завершена!             ║')
    print('╚══════════════════════════════════════╝')
    print(f'\nБэкапы в: {BACKUP_DIR}')
    print('\nСледующие шаги:')
    print('  1. Загрузить новые tenants/ файлы')
    print('  2. Запустить SQL миграцию')
    print('  3. Перезапустить сервисы')


if __name__ == '__main__':
    main()
