"""
Миграция: School → Tenant.

Переименование моделей + реструктуризация полей.
На проде создана 1 School (slug=lectiospace, UUID pk).

!!!!! ВАЖНО: Эту миграцию заменяет 0001_initial (ибо мы по сути
пересоздаём модули). На проде нужно будет:
1. Fake-apply миграцию 0001 (т.к. таблица school уже есть)
2. Выполнить SQL переименование таблиц и колонок
3. Применить эту миграцию для новых таблиц

Стратегия: НЕ менять 0001_initial, а создать 0004 которая:
- Переименует School → Tenant
- Переименует SchoolMembership → TenantMembership
- Добавит новые поля
- Удалит старые поля
- Создаст новые таблицы
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0003_backfill_school_fk'),
    ]

    operations = [
        # ═══════════════════════════════════════
        # 1. Переименование School → Tenant
        # ═══════════════════════════════════════
        migrations.RenameModel(
            old_name='School',
            new_name='Tenant',
        ),
        migrations.RenameModel(
            old_name='SchoolMembership',
            new_name='TenantMembership',
        ),

        # ═══════════════════════════════════════
        # 2. Переименование FK school → tenant (в TenantMembership)
        # ═══════════════════════════════════════
        migrations.RenameField(
            model_name='tenantmembership',
            old_name='school',
            new_name='tenant',
        ),

        # ═══════════════════════════════════════
        # 3. Добавляем новые поля в Tenant
        # ═══════════════════════════════════════
        # uuid (у School pk=UUID, нам нужен отдельный uuid + integer pk)
        # Поскольку School имеет UUID как pk, а Tenant нужен integer pk + uuid field,
        # мы НЕ можем менять pk (это опасно). Оставим UUID pk.
        # Добавим отдельное поле uuid если pk останется UUID.

        # status (вместо is_active boolean)
        migrations.AddField(
            model_name='tenant',
            name='status',
            field=models.CharField(
                choices=[('active', 'Активен'), ('inactive', 'Неактивен'), ('suspended', 'Приостановлен')],
                default='active',
                help_text='Статус',
                max_length=20,
            ),
        ),

        # email
        migrations.AddField(
            model_name='tenant',
            name='email',
            field=models.EmailField(blank=True, default='', help_text='Контактный email', max_length=254),
            preserve_default=False,
        ),

        # phone
        migrations.AddField(
            model_name='tenant',
            name='phone',
            field=models.CharField(blank=True, default='', help_text='Контактный телефон', max_length=30),
            preserve_default=False,
        ),

        # website
        migrations.AddField(
            model_name='tenant',
            name='website',
            field=models.URLField(blank=True, default='', help_text='Сайт'),
            preserve_default=False,
        ),

        # timezone
        migrations.AddField(
            model_name='tenant',
            name='timezone',
            field=models.CharField(default='Europe/Moscow', help_text='Часовой пояс', max_length=50),
        ),

        # locale
        migrations.AddField(
            model_name='tenant',
            name='locale',
            field=models.CharField(default='ru', help_text='Локаль', max_length=10),
        ),

        # metadata (JSON)
        migrations.AddField(
            model_name='tenant',
            name='metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Дополнительные данные'),
        ),

        # ═══════════════════════════════════════
        # 4. Удаляем старые поля School (платёжные, feature flags, etc.)
        # ═══════════════════════════════════════
        migrations.RemoveField(model_name='tenant', name='favicon_url'),
        migrations.RemoveField(model_name='tenant', name='primary_color'),
        migrations.RemoveField(model_name='tenant', name='secondary_color'),
        migrations.RemoveField(model_name='tenant', name='custom_domain'),
        migrations.RemoveField(model_name='tenant', name='yookassa_account_id'),
        migrations.RemoveField(model_name='tenant', name='yookassa_secret_key'),
        migrations.RemoveField(model_name='tenant', name='tbank_terminal_key'),
        migrations.RemoveField(model_name='tenant', name='tbank_password'),
        migrations.RemoveField(model_name='tenant', name='default_payment_provider'),
        migrations.RemoveField(model_name='tenant', name='telegram_bot_token'),
        migrations.RemoveField(model_name='tenant', name='telegram_bot_username'),
        migrations.RemoveField(model_name='tenant', name='monthly_price'),
        migrations.RemoveField(model_name='tenant', name='yearly_price'),
        migrations.RemoveField(model_name='tenant', name='currency'),
        migrations.RemoveField(model_name='tenant', name='revenue_share_percent'),
        migrations.RemoveField(model_name='tenant', name='zoom_enabled'),
        migrations.RemoveField(model_name='tenant', name='google_meet_enabled'),
        migrations.RemoveField(model_name='tenant', name='homework_enabled'),
        migrations.RemoveField(model_name='tenant', name='recordings_enabled'),
        migrations.RemoveField(model_name='tenant', name='finance_enabled'),
        migrations.RemoveField(model_name='tenant', name='concierge_enabled'),
        migrations.RemoveField(model_name='tenant', name='telegram_bot_enabled'),
        migrations.RemoveField(model_name='tenant', name='max_students'),
        migrations.RemoveField(model_name='tenant', name='max_groups'),
        migrations.RemoveField(model_name='tenant', name='max_teachers'),
        migrations.RemoveField(model_name='tenant', name='max_storage_gb'),
        migrations.RemoveField(model_name='tenant', name='is_active'),
        migrations.RemoveField(model_name='tenant', name='is_default'),

        # ═══════════════════════════════════════
        # 5. Обновляем поля TenantMembership
        # ═══════════════════════════════════════
        migrations.AddField(
            model_name='tenantmembership',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # Меняем related_name для user FK
        migrations.AlterField(
            model_name='tenantmembership',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tenant_memberships',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Пользователь',
            ),
        ),

        # Обновляем опции tenant FK
        migrations.AlterField(
            model_name='tenantmembership',
            name='tenant',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='memberships',
                to='tenants.tenant',
                verbose_name='Тенант',
            ),
        ),

        # Обновляем role choices
        migrations.AlterField(
            model_name='tenantmembership',
            name='role',
            field=models.CharField(
                choices=[('owner', 'Владелец'), ('admin', 'Администратор'),
                         ('teacher', 'Преподаватель'), ('student', 'Ученик')],
                default='student',
                max_length=20,
                verbose_name='Роль в org',
            ),
        ),

        # Обновляем owner FK на Tenant (related_name)
        migrations.AlterField(
            model_name='tenant',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                help_text='Пользователь-создатель. Имеет полные права на tenant.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='owned_tenants',
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # Обновляем Meta unique_together
        migrations.AlterUniqueTogether(
            name='tenantmembership',
            unique_together={('tenant', 'user')},
        ),

        # Indexes
        migrations.AddIndex(
            model_name='tenantmembership',
            index=models.Index(fields=['tenant', 'role'], name='membership_tenant_role_idx'),
        ),
        migrations.AddIndex(
            model_name='tenantmembership',
            index=models.Index(fields=['user', 'is_active'], name='membership_user_active_idx'),
        ),

        # Обновляем Meta модели Tenant
        migrations.AlterModelOptions(
            name='tenant',
            options={
                'ordering': ['name'],
                'verbose_name': 'Тенант (орг-я)',
                'verbose_name_plural': 'Тенанты (орг-ии)',
            },
        ),
        migrations.AlterModelOptions(
            name='tenantmembership',
            options={
                'verbose_name': 'Членство в тенанте',
                'verbose_name_plural': 'Членства в тенантах',
            },
        ),

        # ═══════════════════════════════════════
        # 6. Создаём новые модели
        # ═══════════════════════════════════════
        migrations.CreateModel(
            name='TenantResourceLimits',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_teachers', models.PositiveIntegerField(default=10, verbose_name='Макс. преподавателей')),
                ('max_students', models.PositiveIntegerField(default=200, verbose_name='Макс. учеников')),
                ('max_groups', models.PositiveIntegerField(default=50, verbose_name='Макс. групп')),
                ('max_courses', models.PositiveIntegerField(default=20, verbose_name='Макс. курсов')),
                ('max_lessons_per_month', models.PositiveIntegerField(default=100, verbose_name='Макс. уроков/мес')),
                ('max_homeworks', models.PositiveIntegerField(default=50, verbose_name='Макс. ДЗ')),
                ('max_storage_mb', models.PositiveIntegerField(default=5120, verbose_name='Макс. хранилище MB')),
                ('max_recording_hours', models.PositiveIntegerField(default=50, verbose_name='Макс. часов записи')),
                ('max_zoom_accounts', models.PositiveIntegerField(default=2, verbose_name='Макс. Zoom аккаунтов')),
                ('max_concurrent_meetings', models.PositiveIntegerField(default=5, verbose_name='Макс. одновр. встреч')),
                ('api_rate_limit_per_minute', models.PositiveIntegerField(default=120, verbose_name='RPS лимит/мин')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='resource_limits', to='tenants.tenant', verbose_name='Тенант')),
            ],
            options={
                'verbose_name': 'Лимиты ресурсов',
                'verbose_name_plural': 'Лимиты ресурсов',
            },
        ),
        migrations.CreateModel(
            name='TenantUsageStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_teachers', models.PositiveIntegerField(default=0)),
                ('current_students', models.PositiveIntegerField(default=0)),
                ('current_groups', models.PositiveIntegerField(default=0)),
                ('current_courses', models.PositiveIntegerField(default=0)),
                ('current_storage_mb', models.PositiveIntegerField(default=0)),
                ('lessons_this_month', models.PositiveIntegerField(default=0)),
                ('homeworks_total', models.PositiveIntegerField(default=0)),
                ('last_recalculated_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='usage_stats', to='tenants.tenant', verbose_name='Тенант')),
            ],
            options={
                'verbose_name': 'Статистика использования',
                'verbose_name_plural': 'Статистика использования',
            },
        ),
        migrations.CreateModel(
            name='TenantInvite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('role', models.CharField(choices=[('owner', 'Владелец'), ('admin', 'Администратор'), ('teacher', 'Преподаватель'), ('student', 'Ученик')], default='student', max_length=20)),
                ('token', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('accepted', 'Принято'), ('expired', 'Истекло'), ('cancelled', 'Отменено')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('accepted_at', models.DateTimeField(blank=True, null=True)),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tenant_invites_sent', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invites', to='tenants.tenant')),
            ],
            options={
                'verbose_name': 'Приглашение',
                'verbose_name_plural': 'Приглашения',
            },
        ),
        migrations.CreateModel(
            name='TenantVideoSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('local', 'Локальное хранение'), ('kinescope', 'Kinescope'), ('gcs', 'Google Cloud Storage')], default='local', max_length=20)),
                ('kinescope_api_key', models.CharField(blank=True, max_length=200)),
                ('kinescope_project_id', models.CharField(blank=True, max_length=100)),
                ('gcs_bucket_name', models.CharField(blank=True, max_length=200)),
                ('gcs_credentials_json', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='video_settings', to='tenants.tenant')),
            ],
            options={
                'verbose_name': 'Настройки видео',
                'verbose_name_plural': 'Настройки видео',
            },
        ),
    ]
