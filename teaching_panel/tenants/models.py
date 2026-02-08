"""
Модели multi-tenant системы.

School — это "виртуальная онлайн-школа" на базе нашего движка.
Каждый репетитор/школа получает свой поддомен и брендинг.

anna.lectiospace.ru → School(slug='anna', name='English with Anna')
math.lectiospace.ru → School(slug='math', name='Математика Плюс')
"""

import uuid
from django.db import models
from django.conf import settings


class School(models.Model):
    """
    Школа/Tenant — главная модель multi-tenant архитектуры.
    
    Одна School = одна "онлайн-школа" со своим:
    - Брендингом (название, лого, цвета)
    - Поддоменом (slug.lectiospace.ru)
    - Интеграциями (свой YooKassa, Telegram бот)
    - Учениками и учителями (через SchoolMembership)
    - Контентом (группы, уроки, ДЗ)
    
    Пока что:
    - Создаётся одна Default School для текущих данных
    - FK school ещё НЕ добавлен к другим моделям
    - Фильтрация в ViewSets ещё НЕ включена
    
    Следующие шаги:
    1. Добавить school FK к Group, Lesson, Homework
    2. Включить TenantMiddleware
    3. Включить фильтрацию в TenantViewSetMixin
    """
    
    # === Идентификация ===
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        max_length=50, unique=True, db_index=True,
        help_text='Поддомен: slug.lectiospace.ru (только латиница, цифры, дефис)'
    )
    name = models.CharField(
        max_length=200,
        help_text='Название школы (видно ученикам): "English with Anna"'
    )
    
    # === Владелец ===
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Нельзя удалить владельца школы
        related_name='owned_schools',
        help_text='Учитель-владелец школы'
    )
    
    # === Брендинг ===
    logo_url = models.URLField(blank=True, help_text='URL логотипа школы')
    favicon_url = models.URLField(blank=True, help_text='URL favicon школы')
    primary_color = models.CharField(
        max_length=7, default='#4F46E5',
        help_text='Основной цвет бренда (HEX): #4F46E5'
    )
    secondary_color = models.CharField(
        max_length=7, default='#7C3AED',
        help_text='Дополнительный цвет (HEX): #7C3AED'
    )
    
    # === Домены ===
    # Поддомен вычисляется из slug: f"{slug}.lectiospace.ru"
    # Кастомный домен — для premium (teacher.com вместо поддомена)
    custom_domain = models.CharField(
        max_length=200, blank=True, null=True, unique=True,
        help_text='Свой домен (premium): english-anna.com'
    )
    
    # === Платёжные интеграции (per-school) ===
    # Зашифровать через django-encrypted-model-fields когда будет продакшн
    yookassa_account_id = models.CharField(max_length=100, blank=True)
    yookassa_secret_key = models.CharField(max_length=200, blank=True)
    tbank_terminal_key = models.CharField(max_length=100, blank=True)
    tbank_password = models.CharField(max_length=100, blank=True)
    default_payment_provider = models.CharField(
        max_length=20, default='tbank',
        choices=[('yookassa', 'YooKassa'), ('tbank', 'T-Bank')],
    )
    
    # === Telegram интеграция (per-school) ===
    telegram_bot_token = models.CharField(max_length=200, blank=True)
    telegram_bot_username = models.CharField(max_length=100, blank=True)
    
    # === Тарифы для учеников ЭТОЙ школы ===
    monthly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=990,
        help_text='Цена месячной подписки для учеников (RUB)'
    )
    yearly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=9900,
        help_text='Цена годовой подписки (RUB)'
    )
    currency = models.CharField(max_length=3, default='RUB')
    
    # === Revenue Share ===
    revenue_share_percent = models.PositiveIntegerField(
        default=15,
        help_text='Процент владельцу школы от оплат учеников'
    )
    
    # === Feature Flags (per-school) ===
    zoom_enabled = models.BooleanField(default=True)
    google_meet_enabled = models.BooleanField(default=False)
    homework_enabled = models.BooleanField(default=True)
    recordings_enabled = models.BooleanField(default=True)
    finance_enabled = models.BooleanField(default=False)
    concierge_enabled = models.BooleanField(default=False)
    telegram_bot_enabled = models.BooleanField(default=False)
    
    # === Лимиты ===
    max_students = models.PositiveIntegerField(
        default=100, help_text='Максимум учеников в школе'
    )
    max_groups = models.PositiveIntegerField(
        default=20, help_text='Максимум групп'
    )
    max_teachers = models.PositiveIntegerField(
        default=5, help_text='Максимум учителей (кроме владельца)'
    )
    max_storage_gb = models.PositiveIntegerField(
        default=50, help_text='Максимум хранилища (ГБ)'
    )
    
    # === Статус ===
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        help_text='Школа по умолчанию (платформа Lectio Space)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Школа'
        verbose_name_plural = 'Школы'
    
    def __str__(self):
        return f'{self.name} ({self.slug})'
    
    @property
    def subdomain_url(self):
        """URL школы через поддомен."""
        return f'https://{self.slug}.lectiospace.ru'
    
    @property
    def display_url(self):
        """URL для показа пользователю."""
        if self.custom_domain:
            return f'https://{self.custom_domain}'
        return self.subdomain_url
    
    def get_frontend_url(self):
        """URL фронтенда для return_url в платежах."""
        if self.custom_domain:
            return f'https://{self.custom_domain}'
        return self.subdomain_url
    
    def get_payment_credentials(self):
        """Получить платёжные credentials этой школы.
        
        Если у школы нет своих — использовать платформенные из settings.
        """
        from django.conf import settings as django_settings
        platform = django_settings.PLATFORM_CONFIG['integrations']
        
        provider = self.default_payment_provider
        
        if provider == 'yookassa':
            return {
                'provider': 'yookassa',
                'account_id': self.yookassa_account_id or platform['yookassa']['account_id'],
                'secret_key': self.yookassa_secret_key or platform['yookassa']['secret_key'],
            }
        else:  # tbank
            return {
                'provider': 'tbank',
                'terminal_key': self.tbank_terminal_key or platform['tbank']['terminal_key'],
                'password': self.tbank_password or platform['tbank']['password'],
            }
    
    def to_frontend_config(self):
        """Конфиг школы для frontend (публичный, без секретов)."""
        return {
            'id': str(self.id),
            'slug': self.slug,
            'name': self.name,
            'logo_url': self.logo_url,
            'favicon_url': self.favicon_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'custom_domain': self.custom_domain,
            'telegram_bot_username': self.telegram_bot_username,
            'currency': self.currency,
            'features': {
                'zoom': self.zoom_enabled,
                'google_meet': self.google_meet_enabled,
                'homework': self.homework_enabled,
                'recordings': self.recordings_enabled,
                'finance': self.finance_enabled,
                'concierge': self.concierge_enabled,
            },
        }


class SchoolMembership(models.Model):
    """
    Связь User ↔ School.
    
    Один пользователь МОЖЕТ быть в нескольких школах
    (ученик у разных репетиторов, или учитель в нескольких школах).
    Роль определяется per-school (teacher в одной школе может быть student в другой).
    """
    
    ROLE_CHOICES = [
        ('owner', 'Владелец'),
        ('admin', 'Администратор'),
        ('teacher', 'Учитель'),
        ('student', 'Ученик'),
    ]
    
    school = models.ForeignKey(
        School, on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_memberships'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['school', 'user']
        verbose_name = 'Участник школы'
        verbose_name_plural = 'Участники школ'
    
    def __str__(self):
        return f'{self.user.email} → {self.school.name} ({self.role})'
