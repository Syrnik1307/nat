from collections import Counter

from collections import Counter

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum


class ZoomAccount(models.Model):
    """Zoom аккаунт в пуле для распределения лицензий"""
    email = models.EmailField(unique=True)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    zoom_user_id = models.CharField(max_length=255, blank=True)
    
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
    
    def acquire(self):
        """Занять аккаунт для новой встречи"""
        if not self.is_available():
            raise ValueError('Аккаунт недоступен')
        self.current_meetings += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['current_meetings', 'last_used_at', 'updated_at'])
        ZoomPoolUsageMetrics.refresh_usage()
    
    def release(self):
        """Освободить аккаунт после встречи"""
        if self.current_meetings > 0:
            self.current_meetings -= 1
            self.save(update_fields=['current_meetings', 'updated_at'])
            ZoomPoolUsageMetrics.refresh_usage()
    
    @classmethod
    def get_available_for_teacher(cls, teacher):
        """
        Получить доступный аккаунт с учётом teacher affinity
        
        Логика:
        1. Сначала ищем среди preferred для этого teacher
        2. Если нет - берём любой доступный
        3. Сортировка: меньше текущих встреч, позже использовался
        
        Args:
            teacher: объект CustomUser с role='teacher'
            
        Returns:
            ZoomAccount или None
        """
        # Попытка 1: preferred аккаунты для этого teacher
        preferred = cls.objects.filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings'),
            preferred_teachers=teacher
        ).order_by('current_meetings', '-last_used_at').first()
        
        if preferred:
            return preferred
        
        # Попытка 2: любой доступный аккаунт
        available = cls.objects.filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings')
        ).order_by('current_meetings', '-last_used_at').first()
        
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
