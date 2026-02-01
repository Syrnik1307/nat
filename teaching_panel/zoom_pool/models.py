from collections import Counter

from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, F
import logging

logger = logging.getLogger(__name__)


class ZoomAccount(models.Model):
    """
    Zoom аккаунт в пуле для распределения лицензий.
    
    Каждый ZoomAccount соответствует отдельному Zoom Server-to-Server OAuth приложению.
    Credentials хранятся здесь, а не в глобальных settings.
    
    PRODUCTION SAFETY:
    - acquire() и release() используют атомарные транзакции
    - row-level locking предотвращает race conditions
    - Mock credentials блокируются в production (DEBUG=False)
    """
    # Mock/test credentials - БЛОКИРУЮТСЯ в production
    INVALID_CREDENTIALS = frozenset({'bad', 'test', 'invalid', 'demo', 'placeholder', 'xxx', '123', 'mock'})
    
    email = models.EmailField(unique=True)
    
    # Server-to-Server OAuth credentials (обязательные)
    zoom_account_id = models.CharField(
        max_length=255,
        default='',
        blank=True,
        help_text='Account ID из Zoom Server-to-Server OAuth App'
    )
    api_key = models.CharField(
        max_length=255,
        help_text='Client ID из Zoom Server-to-Server OAuth App'
    )
    api_secret = models.CharField(
        max_length=255,
        help_text='Client Secret из Zoom Server-to-Server OAuth App'
    )
    zoom_user_id = models.CharField(
        max_length=255, 
        blank=True,
        default='me',
        help_text='User ID в Zoom (обычно "me" или email)'
    )
    
    max_concurrent_meetings = models.IntegerField(default=1)
    current_meetings = models.IntegerField(default=0)
    
    # Teacher affinity: приоритетные преподаватели для этого аккаунта
    preferred_teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='preferred_zoom_accounts',
        limit_choices_to={'role': 'teacher'},
        help_text='Преподаватели, которым этот аккаунт назначается приоритетно'
    )
    
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['current_meetings', '-last_used_at']
        verbose_name = 'Zoom Account'
        verbose_name_plural = 'Zoom Accounts'
    
    def __str__(self):
        return f"{self.email} ({self.current_meetings}/{self.max_concurrent_meetings})"
    
    def is_available(self):
        """Проверка доступности аккаунта"""
        return self.is_active and self.current_meetings < self.max_concurrent_meetings
    
    def is_mock_account(self):
        """Проверка, является ли аккаунт Mock/тестовым"""
        if not self.zoom_account_id:
            return True
        return self.zoom_account_id.lower() in self.INVALID_CREDENTIALS
    
    def validate_for_production(self):
        """
        Проверка что аккаунт можно использовать в production.
        
        Raises:
            ValueError: если аккаунт Mock и DEBUG=False
        """
        if not settings.DEBUG and self.is_mock_account():
            raise ValueError(
                f"PRODUCTION SAFETY: Zoom account {self.email} has mock/invalid credentials. "
                f"Mock accounts cannot be used when DEBUG=False. "
                f"Please configure real Zoom credentials."
            )
    
    def acquire(self):
        """
        Занять аккаунт для новой встречи.
        
        PRODUCTION-GRADE:
        - Атомарная транзакция с row-level locking
        - Проверка Mock credentials в production
        - Возвращает self для chaining
        
        Raises:
            ValueError: если аккаунт недоступен или Mock в production
        """
        # Block mock accounts in production
        self.validate_for_production()
        
        with transaction.atomic():
            # Re-fetch with lock to prevent race condition
            locked_account = (
                ZoomAccount.objects
                .select_for_update(nowait=False)
                .get(pk=self.pk)
            )
            
            if not locked_account.is_available():
                raise ValueError(
                    f'Zoom account {self.email} недоступен: '
                    f'{locked_account.current_meetings}/{locked_account.max_concurrent_meetings} meetings'
                )
            
            locked_account.current_meetings = F('current_meetings') + 1
            locked_account.last_used_at = timezone.now()
            locked_account.save(update_fields=['current_meetings', 'last_used_at', 'updated_at'])
            
            # Refresh to get actual value after F() expression
            locked_account.refresh_from_db()
            
            # Update self to match
            self.current_meetings = locked_account.current_meetings
            self.last_used_at = locked_account.last_used_at
        
        logger.info(f"[ZOOM_POOL] Acquired account {self.email}, now {self.current_meetings}/{self.max_concurrent_meetings}")
        
        # Update pool metrics asynchronously (best effort)
        try:
            ZoomPoolUsageMetrics.refresh_usage()
        except Exception as e:
            logger.warning(f"[ZOOM_POOL] Failed to refresh metrics: {e}")
        
        return self
    
    def release(self):
        """
        Освободить аккаунт после встречи.
        
        PRODUCTION-GRADE:
        - Атомарная транзакция с row-level locking
        - Защита от отрицательных значений
        - Идемпотентность (повторные вызовы безопасны)
        """
        with transaction.atomic():
            # Re-fetch with lock
            locked_account = (
                ZoomAccount.objects
                .select_for_update(nowait=False)
                .get(pk=self.pk)
            )
            
            if locked_account.current_meetings > 0:
                locked_account.current_meetings = F('current_meetings') - 1
                locked_account.save(update_fields=['current_meetings', 'updated_at'])
                
                # Refresh to get actual value
                locked_account.refresh_from_db()
                self.current_meetings = locked_account.current_meetings
                
                logger.info(f"[ZOOM_POOL] Released account {self.email}, now {self.current_meetings}/{self.max_concurrent_meetings}")
            else:
                logger.warning(f"[ZOOM_POOL] Account {self.email} already at 0 meetings, skipping release")
        
        # Update metrics (best effort)
        try:
            ZoomPoolUsageMetrics.refresh_usage()
        except Exception as e:
            logger.warning(f"[ZOOM_POOL] Failed to refresh metrics: {e}")
    
    @classmethod
    def get_available_for_teacher(cls, teacher):
        """
        Получить доступный аккаунт с учётом teacher affinity.
        
        PRODUCTION-GRADE:
        - Исключает Mock/тестовые аккаунты в production
        - Сортировка: меньше текущих встреч, позже использовался
        
        Логика:
        1. Сначала ищем среди preferred для этого teacher
        2. Если нет - берём любой доступный
        
        Args:
            teacher: объект CustomUser с role='teacher'
            
        Returns:
            ZoomAccount или None
        """
        # Base queryset - exclude mock accounts in production
        base_qs = cls.objects.filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings'),
        )
        
        # In production, exclude mock/invalid credentials
        if not settings.DEBUG:
            for invalid in cls.INVALID_CREDENTIALS:
                base_qs = base_qs.exclude(zoom_account_id__iexact=invalid)
            # Also exclude empty credentials
            base_qs = base_qs.exclude(zoom_account_id='').exclude(zoom_account_id__isnull=True)
        
        # Попытка 1: preferred аккаунты для этого teacher
        preferred = base_qs.filter(
            preferred_teachers=teacher
        ).order_by('current_meetings', '-last_used_at').first()
        
        if preferred:
            logger.info(f"[ZOOM_POOL] Found preferred account {preferred.email} for teacher {teacher.email}")
            return preferred
        
        # Попытка 2: любой доступный аккаунт
        available = base_qs.order_by('current_meetings', '-last_used_at').first()
        
        if available:
            logger.info(f"[ZOOM_POOL] Found available account {available.email} for teacher {teacher.email}")
        else:
            logger.warning(f"[ZOOM_POOL] No available accounts for teacher {teacher.email}")
        
        return available


class ZoomPoolUsageMetrics(models.Model):
    """Глобальная статистика использования Zoom пулов"""
    current_in_use = models.IntegerField(default=0)
    peak_in_use = models.IntegerField(default=0)
    current_sessions = models.IntegerField(default=0)
    peak_sessions = models.IntegerField(default=0)
    stats_month = models.DateField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Zoom Pool Usage Metric'
        verbose_name_plural = 'Zoom Pool Usage Metrics'
    
    def __str__(self):
        return f"current={self.current_in_use}, peak={self.peak_in_use}"
    
    @classmethod
    def get_solo(cls):
        metrics, _ = cls.objects.get_or_create(id=1)
        return metrics
    
    @classmethod
    def refresh_usage(cls):
        """Пересчитать статистику по текущим данным аккаунтов."""
        from schedule.models import Lesson

        now = timezone.now()
        grace_before = timezone.timedelta(minutes=15)
        grace_after = timezone.timedelta(minutes=5)

        active_lessons = Lesson.objects.filter(
            zoom_account__isnull=False,
            start_time__lte=now + grace_before,
            end_time__gte=now - grace_after,
        )

        lesson_counts = Counter(active_lessons.values_list('zoom_account_id', flat=True))

        # Синхронизируем current_meetings с фактическими занятиями
        timestamp = timezone.now()
        accounts = list(ZoomAccount.objects.all())
        to_update = []
        for account in accounts:
            new_count = lesson_counts.get(account.id, 0)
            if account.current_meetings != new_count:
                account.current_meetings = new_count
                account.updated_at = timestamp
                to_update.append(account)
        if to_update:
            ZoomAccount.objects.bulk_update(to_update, ['current_meetings', 'updated_at'])

        active_accounts = [acc for acc in accounts if acc.is_active]
        current_in_use = sum(1 for acc in active_accounts if acc.current_meetings > 0)
        current_sessions = sum(acc.current_meetings for acc in active_accounts)
        metrics = cls.get_solo()
        fields_to_update = []

        current_month = timezone.localdate().replace(day=1)
        if metrics.stats_month != current_month:
            metrics.stats_month = current_month
            metrics.peak_in_use = 0
            metrics.peak_sessions = 0
            fields_to_update.extend(['stats_month', 'peak_in_use', 'peak_sessions'])
        if metrics.current_in_use != current_in_use:
            metrics.current_in_use = current_in_use
            fields_to_update.append('current_in_use')
        if current_in_use > metrics.peak_in_use:
            metrics.peak_in_use = current_in_use
            if 'peak_in_use' not in fields_to_update:
                fields_to_update.append('peak_in_use')
        if metrics.current_sessions != current_sessions:
            metrics.current_sessions = current_sessions
            fields_to_update.append('current_sessions')
        if current_sessions > metrics.peak_sessions:
            metrics.peak_sessions = current_sessions
            if 'peak_sessions' not in fields_to_update:
                fields_to_update.append('peak_sessions')
        if fields_to_update:
            fields_to_update.append('updated_at')
            metrics.save(update_fields=fields_to_update)
        return metrics
