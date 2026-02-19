"""
Tenant models — ядро мультитенантной архитектуры.

Подход: shared-database, shared-schema с tenant FK на каждой модели верхнего уровня.
Tenant = организация / учебный центр / школа.
"""

import uuid
from django.db import models
from django.conf import settings


class Tenant(models.Model):
    """
    Организация (школа, учебный центр, репетитор).
    Все данные в системе привязаны к tenant через FK.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активен'
        INACTIVE = 'inactive', 'Неактивен'
        SUSPENDED = 'suspended', 'Приостановлен'

    # === Идентификация ===
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        max_length=50, unique=True, db_index=True,
        help_text='Уникальный идентификатор (для URL/субдомена)'
    )
    name = models.CharField(max_length=200, help_text='Название организации')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
        help_text='Статус',
    )

    # === Владелец ===
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_tenants',
        help_text='Пользователь-создатель. Имеет полные права на tenant.',
        null=True, blank=True,
    )

    # === Контакты ===
    email = models.EmailField(blank=True, help_text='Контактный email')
    phone = models.CharField(max_length=30, blank=True, help_text='Контактный телефон')
    website = models.URLField(blank=True, help_text='Сайт')
    logo_url = models.URLField(blank=True, help_text='Логотип')

    # === Локализация ===
    timezone = models.CharField(max_length=50, default='Europe/Moscow', help_text='Часовой пояс')
    locale = models.CharField(max_length=10, default='ru', help_text='Локаль')

    # === Дополнительные данные (JSON) ===
    metadata = models.JSONField(default=dict, blank=True, help_text='Дополнительные данные')

    # === Даты ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тенант (орг-я)'
        verbose_name_plural = 'Тенанты (орг-ии)'

    def __str__(self):
        return f'{self.name} ({self.slug})'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    def to_frontend_config(self):
        """Возвращает конфиг тенанта для фронтенда (используется в /api/me/ и др.)."""
        theme = (self.metadata or {}).get('theme', {})
        features_meta = (self.metadata or {}).get('features', {})
        return {
            'id': str(self.id),
            'slug': self.slug,
            'name': self.name,
            'logo_url': self.logo_url or '',
            'primary_color': theme.get('primary_color', '#1976d2'),
            'secondary_color': theme.get('secondary_color', '#f5f5f5'),
            'features': {
                'zoom': features_meta.get('zoom', True),
                'homework': features_meta.get('homework', True),
                'recordings': features_meta.get('recordings', False),
                'finance': features_meta.get('finance', False),
            },
        }


class TenantMembership(models.Model):
    """
    M2M-связь пользователя с тенантом.
    Один пользователь может состоять в нескольких tenant'ах с разными ролями.
    """

    class TenantRole(models.TextChoices):
        OWNER = 'owner', 'Владелец'
        ADMIN = 'admin', 'Администратор'
        TEACHER = 'teacher', 'Преподаватель'
        STUDENT = 'student', 'Ученик'

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Тенант',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships',
        verbose_name='Пользователь',
    )
    role = models.CharField(
        max_length=20, choices=TenantRole.choices,
        default=TenantRole.STUDENT,
        verbose_name='Роль в org',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата вступления')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Членство в тенанте'
        verbose_name_plural = 'Членства в тенантах'
        unique_together = ['tenant', 'user']
        indexes = [
            models.Index(fields=['tenant', 'role'], name='membership_tenant_role_idx'),
            models.Index(fields=['user', 'is_active'], name='membership_user_active_idx'),
        ]

    def __str__(self):
        return f'{self.user} → {self.tenant} ({self.role})'


class TenantResourceLimits(models.Model):
    """
    Лимиты ресурсов для tenant'а (quotas).
    Один Tenant → один TenantResourceLimits (OneToOne).
    """
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE,
        related_name='resource_limits',
        verbose_name='Тенант',
    )
    max_teachers = models.PositiveIntegerField(default=10, verbose_name='Макс. преподавателей')
    max_students = models.PositiveIntegerField(default=200, verbose_name='Макс. учеников')
    max_groups = models.PositiveIntegerField(default=50, verbose_name='Макс. групп')
    max_courses = models.PositiveIntegerField(default=20, verbose_name='Макс. курсов')
    max_lessons_per_month = models.PositiveIntegerField(default=100, verbose_name='Макс. уроков/мес')
    max_homeworks = models.PositiveIntegerField(default=50, verbose_name='Макс. ДЗ')
    max_storage_mb = models.PositiveIntegerField(default=5120, verbose_name='Макс. хранилище MB')
    max_recording_hours = models.PositiveIntegerField(default=50, verbose_name='Макс. часов записи')
    max_zoom_accounts = models.PositiveIntegerField(default=2, verbose_name='Макс. Zoom аккаунтов')
    max_concurrent_meetings = models.PositiveIntegerField(default=5, verbose_name='Макс. одновр. встреч')
    api_rate_limit_per_minute = models.PositiveIntegerField(default=120, verbose_name='RPS лимит/мин')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Лимиты ресурсов'
        verbose_name_plural = 'Лимиты ресурсов'

    def __str__(self):
        return f'Limits: {self.tenant}'


class TenantUsageStats(models.Model):
    """
    Текущее использование ресурсов tenant'ом (обновляется периодически).
    """
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE,
        related_name='usage_stats',
        verbose_name='Тенант',
    )
    current_teachers = models.PositiveIntegerField(default=0)
    current_students = models.PositiveIntegerField(default=0)
    current_groups = models.PositiveIntegerField(default=0)
    current_courses = models.PositiveIntegerField(default=0)
    current_storage_mb = models.PositiveIntegerField(default=0)
    lessons_this_month = models.PositiveIntegerField(default=0)
    homeworks_total = models.PositiveIntegerField(default=0)
    last_recalculated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Статистика использования'
        verbose_name_plural = 'Статистика использования'

    def __str__(self):
        return f'Usage: {self.tenant}'

    def recalculate(self):
        """Пересчитать текущее использование из БД."""
        from django.utils import timezone
        tenant = self.tenant
        memberships = TenantMembership.objects.filter(tenant=tenant, is_active=True)
        self.current_teachers = memberships.filter(role='teacher').count()
        self.current_students = memberships.filter(role='student').count()
        self.last_recalculated_at = timezone.now()
        self.save()


class TenantInvite(models.Model):
    """Приглашение в tenant."""

    class InviteStatus(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        ACCEPTED = 'accepted', 'Принято'
        EXPIRED = 'expired', 'Истекло'
        CANCELLED = 'cancelled', 'Отменено'

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE,
        related_name='invites',
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=TenantMembership.TenantRole.choices,
        default=TenantMembership.TenantRole.STUDENT,
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(
        max_length=20,
        choices=InviteStatus.choices,
        default=InviteStatus.PENDING,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tenant_invites_sent',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Приглашение'
        verbose_name_plural = 'Приглашения'

    def __str__(self):
        return f'Invite {self.email} → {self.tenant} ({self.status})'


class TenantVideoSettings(models.Model):
    """Настройки видео-провайдера для tenant'а."""

    class VideoProvider(models.TextChoices):
        LOCAL = 'local', 'Локальное хранение'
        KINESCOPE = 'kinescope', 'Kinescope'
        GCS = 'gcs', 'Google Cloud Storage'

    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE,
        related_name='video_settings',
    )
    provider = models.CharField(
        max_length=20,
        choices=VideoProvider.choices,
        default=VideoProvider.LOCAL,
    )
    kinescope_api_key = models.CharField(max_length=200, blank=True)
    kinescope_project_id = models.CharField(max_length=100, blank=True)
    gcs_bucket_name = models.CharField(max_length=200, blank=True)
    gcs_credentials_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки видео'
        verbose_name_plural = 'Настройки видео'

    def __str__(self):
        return f'Video: {self.tenant} ({self.provider})'


# ══════════════════════════════════════════════════════════════════════════════
# Backward-compatible aliases: School → Tenant, SchoolMembership → TenantMembership
# Нужны для старых тестов и миграций, которые ссылаются на School/SchoolMembership.
# ══════════════════════════════════════════════════════════════════════════════
School = Tenant
SchoolMembership = TenantMembership
