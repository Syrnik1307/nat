from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class SystemStatus(models.Model):
    """Статус системы для страницы /status и инцидент-режима"""
    
    STATUS_CHOICES = (
        ('operational', 'Всё работает'),
        ('degraded', 'Частичные проблемы'),
        ('major_outage', 'Серьёзный сбой'),
        ('maintenance', 'Техобслуживание'),
    )
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='operational'
    )
    message = models.TextField(
        'Сообщение',
        blank=True,
        default='',
        help_text='Публичное сообщение о статусе'
    )
    incident_title = models.CharField(
        'Название инцидента',
        max_length=200,
        blank=True,
        default=''
    )
    incident_started_at = models.DateTimeField(
        'Начало инцидента',
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    updated_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Обновил'
    )
    
    class Meta:
        verbose_name = 'Статус системы'
        verbose_name_plural = 'Статус системы'
    
    def __str__(self):
        return f"{self.get_status_display()} - {self.updated_at}"
    
    @classmethod
    def get_current(cls):
        """Получить текущий статус (singleton)"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    
    def start_incident(self, title, message='', user=None):
        """Начать инцидент"""
        self.status = 'major_outage'
        self.incident_title = title
        self.message = message
        self.incident_started_at = timezone.now()
        self.updated_by = user
        self.save()
    
    def resolve_incident(self, message='', user=None):
        """Завершить инцидент"""
        self.status = 'operational'
        self.message = message or 'Проблема решена'
        self.incident_title = ''
        self.incident_started_at = None
        self.updated_by = user
        self.save()


class SupportTicket(models.Model):
    """Обращения в поддержку"""
    
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('waiting_user', 'Ожидает ответа пользователя'),
        ('resolved', 'Решён'),
        ('closed', 'Закрыт'),
    )
    
    # P0-P3 маппинг для SLA
    PRIORITY_CHOICES = (
        ('p0', 'P0 - Инцидент (всем плохо)'),
        ('p1', 'P1 - Критично (блокирует работу)'),
        ('p2', 'P2 - Важно (есть обходной путь)'),
        ('p3', 'P3 - Низкий (вопрос/пожелание)'),
    )
    
    # SLA в минутах для первого ответа
    PRIORITY_SLA = {
        'p0': 15,   # 15 минут
        'p1': 120,  # 2 часа
        'p2': 480,  # 8 часов (1 рабочий день)
        'p3': 1440, # 24 часа
    }
    
    CATEGORY_CHOICES = (
        ('login', 'Вход/Регистрация'),
        ('payment', 'Оплата/Подписка'),
        ('lesson', 'Уроки/Расписание'),
        ('zoom', 'Zoom/Видеосвязь'),
        ('homework', 'Домашние задания'),
        ('recording', 'Записи уроков'),
        ('other', 'Другое'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name='Пользователь',
        null=True,
        blank=True,
        help_text='Может быть пустым для анонимных обращений'
    )
    
    # Для анонимных обращений
    email = models.EmailField('Email', blank=True, default='')
    name = models.CharField('Имя', max_length=100, blank=True, default='')
    
    subject = models.CharField('Тема', max_length=200)
    description = models.TextField('Описание проблемы')
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    
    priority = models.CharField(
        'Приоритет',
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='p2'
    )
    
    category = models.CharField(
        'Категория',
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text='Категория проблемы для быстрого триажа'
    )
    
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name='assigned_tickets',
        verbose_name='Назначено',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    resolved_at = models.DateTimeField('Решено', null=True, blank=True)
    first_response_at = models.DateTimeField('Первый ответ', null=True, blank=True)
    
    # Технические данные (расширенный контекст)
    user_agent = models.TextField('User Agent', blank=True, default='')
    page_url = models.TextField('URL страницы', blank=True, default='')
    screenshot = models.TextField('Скриншот (base64)', blank=True, default='')
    
    # Расширенный контекст для быстрой диагностики
    build_version = models.CharField('Версия билда', max_length=50, blank=True, default='')
    user_role = models.CharField('Роль пользователя', max_length=20, blank=True, default='')
    subscription_status = models.CharField('Статус подписки', max_length=50, blank=True, default='')
    browser_info = models.CharField('Браузер', max_length=100, blank=True, default='')
    screen_resolution = models.CharField('Разрешение экрана', max_length=20, blank=True, default='')
    error_message = models.TextField('Сообщение об ошибке', blank=True, default='')
    steps_to_reproduce = models.TextField('Шаги воспроизведения', blank=True, default='')
    expected_behavior = models.TextField('Ожидаемое поведение', blank=True, default='')
    actual_behavior = models.TextField('Фактическое поведение', blank=True, default='')
    
    # Источник обращения
    SOURCE_CHOICES = (
        ('web', 'Веб-форма'),
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('admin', 'Создано админом'),
    )
    source = models.CharField(
        'Источник',
        max_length=20,
        choices=SOURCE_CHOICES,
        default='web'
    )
    
    class Meta:
        verbose_name = 'Обращение в поддержку'
        verbose_name_plural = 'Обращения в поддержку'
        ordering = ['-created_at']
    
    def __str__(self):
        user_info = self.user.email if self.user else self.email or 'Аноним'
        return f"#{self.id} {self.subject} - {user_info}"
    
    @property
    def sla_minutes(self):
        """SLA в минутах для этого приоритета"""
        return self.PRIORITY_SLA.get(self.priority, 480)
    
    @property
    def sla_deadline(self):
        """Дедлайн для первого ответа"""
        from datetime import timedelta
        return self.created_at + timedelta(minutes=self.sla_minutes)
    
    @property
    def sla_breached(self):
        """SLA нарушен?"""
        if self.first_response_at:
            return self.first_response_at > self.sla_deadline
        return timezone.now() > self.sla_deadline
    
    @property
    def time_to_first_response(self):
        """Время до первого ответа в минутах"""
        if self.first_response_at:
            delta = self.first_response_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None
    
    def record_first_response(self):
        """Записать время первого ответа"""
        if not self.first_response_at:
            self.first_response_at = timezone.now()
            self.save(update_fields=['first_response_at'])
    
    def mark_resolved(self):
        """Пометить как решённое"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()
    
    def save(self, *args, **kwargs):
        """Переопределяем save для отправки уведомлений"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Если это новый тикет, отправляем уведомление админам
        if is_new:
            self._send_telegram_notification()
    
    def _send_telegram_notification(self):
        """Отправка уведомления в Telegram о новом тикете"""
        import os

        import requests

        token = os.getenv('SUPPORT_BOT_TOKEN')
        if not token:
            return

        broadcast_chat_id = (os.getenv('SUPPORT_NOTIFICATIONS_CHAT_ID') or '').strip()

        chat_ids = set()
        if broadcast_chat_id:
            chat_ids.add(broadcast_chat_id)

        # Получаем всех админов с Telegram ID (личные уведомления)
        admins = list(CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False).exclude(telegram_id__exact=''))
        for admin in admins:
            chat_ids.add(str(admin.telegram_id).strip())

        if not chat_ids:
            return
        
        priority_emoji = {
            'p0': '🔴🔴🔴',  # Инцидент - максимальное внимание
            'p1': '🔴',
            'p2': '🟡',
            'p3': '🟢'
        }.get(self.priority, '⚪')
        
        category_display = dict(self.CATEGORY_CHOICES).get(self.category, self.category)
        user_info = self.user.get_full_name() if self.user else self.email or 'Аноним'
        sla_text = f"⏱️ SLA: {self.sla_minutes} мин"
        
        # Дополнительный контекст для быстрой диагностики
        context_lines = []
        if self.user_role:
            context_lines.append(f"👤 Роль: {self.user_role}")
        if self.subscription_status:
            context_lines.append(f"💳 Подписка: {self.subscription_status}")
        if self.error_message:
            context_lines.append(f"❌ Ошибка: {self.error_message[:100]}")
        context_str = '\n'.join(context_lines) if context_lines else ''
        
        message = (
            f"🆕 *Новый тикет #{self.id}*\n\n"
            f"{priority_emoji} *Приоритет:* {self.get_priority_display()}\n"
            f"{sla_text}\n"
            f"🏷️ *Категория:* {category_display}\n"
            f"📝 *Тема:* {self.subject}\n"
            f"📄 *Описание:*\n{self.description[:200]}{'...' if len(self.description) > 200 else ''}\n\n"
            f"👤 *От:* {user_info}\n"
            f"{context_str}\n\n"
            f"Для просмотра: /view\\_{self.id}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'text': message,
            'parse_mode': 'Markdown',
        }

        for chat_id in chat_ids:
            try:
                requests.post(url, json={**payload, 'chat_id': chat_id}, timeout=5)
            except Exception:
                # Best-effort only
                continue


class SupportMessage(models.Model):
    """Сообщения в тикете"""
    
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Тикет'
    )
    
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='support_messages',
        verbose_name='Автор',
        null=True,
        blank=True
    )
    
    is_staff_reply = models.BooleanField(
        'Ответ от поддержки',
        default=False
    )
    
    message = models.TextField('Сообщение')
    
    attachments = models.TextField(
        'Вложения (JSON)',
        blank=True,
        default='',
        help_text='JSON список ссылок на файлы'
    )
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    read_by_user = models.BooleanField('Прочитано пользователем', default=False)
    read_by_staff = models.BooleanField('Прочитано поддержкой', default=False)
    
    class Meta:
        verbose_name = 'Сообщение поддержки'
        verbose_name_plural = 'Сообщения поддержки'
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if not is_new:
            return

        # Best-effort уведомления, чтобы работало и для сообщений,
        # созданных напрямую из Telegram-бота (без вызова API endpoint).
        try:
            from .telegram_notifications import notify_admins_new_message, notify_user_staff_reply

            if self.is_staff_reply:
                notify_user_staff_reply(ticket=self.ticket, message=self)
            else:
                if not getattr(self, '_skip_notify_admins', False):
                    notify_admins_new_message(ticket=self.ticket, message=self)
        except Exception:
            return
    
    def __str__(self):
        author_name = self.author.email if self.author else 'Аноним'
        return f"Message from {author_name} in ticket #{self.ticket.id}"


class QuickSupportResponse(models.Model):
    """Быстрые ответы для поддержки"""
    
    title = models.CharField('Заголовок', max_length=100)
    message = models.TextField('Текст ответа')
    category = models.CharField('Категория', max_length=50, blank=True, default='')
    usage_count = models.IntegerField('Использований', default=0)
    is_active = models.BooleanField('Активен', default=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Быстрый ответ'
        verbose_name_plural = 'Быстрые ответы'
        ordering = ['-usage_count', 'title']
    
    def __str__(self):
        return self.title


class SupportAttachment(models.Model):
    """Файловые вложения к тикетам/сообщениям поддержки.

    Паттерн хранения аналогичен HomeworkFile: файл сохраняется
    на диск в MEDIA_ROOT/support_files/, доступ через прокси-endpoint.
    """

    id = models.CharField(
        primary_key=True,
        max_length=32,
        editable=False,
        default='',
    )
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='Тикет',
        null=True,
        blank=True,
    )
    message = models.ForeignKey(
        SupportMessage,
        on_delete=models.CASCADE,
        related_name='file_attachments',
        verbose_name='Сообщение',
        null=True,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Загрузил',
    )
    original_name = models.CharField('Имя файла', max_length=255)
    mime_type = models.CharField('MIME-тип', max_length=100)
    size = models.PositiveIntegerField('Размер (байт)', default=0)
    local_path = models.CharField('Путь на диске', max_length=500, blank=True, default='')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Вложение поддержки'
        verbose_name_plural = 'Вложения поддержки'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.original_name} ({self.size} bytes)"

    def save(self, *args, **kwargs):
        if not self.id:
            import uuid
            self.id = uuid.uuid4().hex
        super().save(*args, **kwargs)
