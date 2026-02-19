#!/usr/bin/env python
"""
Создание тенанта «Ольга фарфоровые цветы» со всеми необходимыми данными.

Запуск:
    python manage.py shell < create_olga_tenant.py

    или

    python manage.py shell -c "exec(open('create_olga_tenant.py').read())"
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.db import transaction
from tenants.models import Tenant, TenantMembership, TenantResourceLimits, TenantUsageStats


def create_olga_tenant():
    """Создаёт тенант 'Ольга фарфоровые цветы' с кастомным брендингом и лимитами."""

    tenant_slug = os.environ.get('OLGA_TENANT_SLUG', 'olga')
    base_domain = os.environ.get('BASE_DOMAIN', 'yourdomain.com')
    owner_email = os.environ.get('OLGA_OWNER_EMAIL', 'info@olgaflowers.ru')
    website = os.environ.get('OLGA_WEBSITE', f'https://{tenant_slug}.{base_domain}')

    print("=" * 60)
    print("СОЗДАНИЕ ТЕНАНТА: Ольга фарфоровые цветы")
    print("=" * 60)

    with transaction.atomic():
        # 1. Создаём тенант
        tenant, created = Tenant.objects.get_or_create(
            slug=tenant_slug,
            defaults={
                'name': 'Ольга фарфоровые цветы',
                'status': 'active',
                'email': owner_email,
                'phone': '+7 (999) 123-45-67',
                'website': website,
                'logo_url': '',  # Заполнить после загрузки логотипа
                'timezone': 'Europe/Moscow',
                'locale': 'ru',
                'metadata': {
                    # Тема / брендинг
                    'theme': {
                        'primary_color': '#c49a6c',       # тёплый золотистый
                        'secondary_color': '#f5f0eb',     # нежный фон
                        'accent_color': '#8b5e3c',        # коричневый акцент
                        'font_family': 'Georgia, serif',
                    },
                    # SEO
                    'seo': {
                        'title': 'Ольга фарфоровые цветы — авторские изделия из фарфора',
                        'description': 'Уникальные фарфоровые цветы ручной работы. '
                                       'Каждый цветок — произведение искусства.',
                        'keywords': 'фарфоровые цветы, фарфор, авторские изделия, '
                                    'ручная работа, Ольга',
                        'og_image': '',  # Заполнить
                    },
                    # Контакты для витрины
                    'contacts': {
                        'address': 'Москва, ул. Примерная, д. 1',
                        'instagram': '@olga_porcelain',
                        'telegram': '@olga_flowers',
                        'whatsapp': '+79991234567',
                    },
                    # Опциональный кастомный email-отправитель
                    'from_email': 'hello@olgaflowers.ru',
                    # Платежи: временный режим без реальной кассы
                    'payments': {
                        'stub_mode': True,
                    },
                },
            },
        )

        if created:
            print(f"[OK] Тенант создан: {tenant.name} (slug={tenant.slug}, uuid={tenant.uuid})")
        else:
            print(f"[INFO] Тенант уже существует: {tenant.name}")

        # 2. Ресурсные лимиты (для витрины/магазина — скромные)
        limits, _ = TenantResourceLimits.objects.get_or_create(
            tenant=tenant,
            defaults={
                'max_teachers': 3,          # Ольга + помощники
                'max_students': 50,         # Покупатели / подписчики
                'max_groups': 5,
                'max_courses': 5,           # Коллекции
                'max_lessons_per_month': 30,
                'max_homeworks': 20,
                'max_storage_mb': 2048,     # 2 GB для фото
                'max_recording_hours': 10,
                'max_zoom_accounts': 1,
                'max_concurrent_meetings': 2,
                'api_rate_limit_per_minute': 60,
            },
        )
        print(f"[OK] Лимиты ресурсов: max_storage={limits.max_storage_mb}MB")

        # 3. Статистика использования
        TenantUsageStats.objects.get_or_create(tenant=tenant)
        print("[OK] Статистика использования создана")

        # 4. Попытка привязать owner
        # Если есть пользователь с email владельца — сделать owner
        from accounts.models import CustomUser
        owner_user = CustomUser.objects.filter(email=owner_email).first()

        if owner_user:
            tenant.owner = owner_user
            tenant.save(update_fields=['owner'])
            TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=owner_user,
                defaults={'role': 'owner', 'is_active': True},
            )
            print(f"[OK] Owner привязан: {owner_user.email}")
        else:
            print(f"[WARN] Пользователь {owner_email} не найден.")
            print("   Создайте пользователя и вручную привяжите через:")
            print(f"   TenantMembership.objects.create(tenant_id={tenant.id}, user=user, role='owner')")
            print(f"   Tenant.objects.filter(id={tenant.id}).update(owner=user)")

    print()
    print("=" * 60)
    print("ТЕНАНТ ГОТОВ")
    print(f"  Slug:  {tenant.slug}")
    print(f"  UUID:  {tenant.uuid}")
    print(f"  URL:   https://{tenant.slug}.{base_domain}")
    print(f"  API:   GET /api/tenants/public/{tenant.slug}/branding/")
    print("=" * 60)
    print()
    print("Следующие шаги:")
    print(f"  1. Настроить DNS: {tenant.slug}.{base_domain} → IP сервера")
    print(f"  2. Получить wildcard SSL (или отдельный для {tenant.slug}.{base_domain})")
    print("  3. Загрузить логотип и обновить tenant.logo_url")
    print("  4. Создать пользователя-владельца и привязать через TenantMembership")

    return tenant


if __name__ == '__main__':
    create_olga_tenant()
else:
    create_olga_tenant()
