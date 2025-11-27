from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class SupportTicket(models.Model):
    """Обращения в поддержку"""
    
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('waiting_user', 'Ожидает ответа пользователя'),
        ('resolved', 'Решён'),
        ('closed', 'Закрыт'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
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
        default='normal'
    )
    
    category = models.CharField(
        'Категория',
        max_length=50,
        blank=True,
        default='',
        help_text='Техническая проблема, Вопрос по функционалу и т.д.'
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
    
    # Технические данные
    user_agent = models.TextField('User Agent', blank=True, default='')
    page_url = models.TextField('URL страницы', blank=True, default='')
    screenshot = models.TextField('Скриншот (base64)', blank=True, default='')
    
    class Meta:
        verbose_name = 'Обращение в поддержку'
        verbose_name_plural = 'Обращения в поддержку'
        ordering = ['-created_at']
    
    def __str__(self):
        user_info = self.user.email if self.user else self.email or 'Аноним'
        return f"#{self.id} {self.subject} - {user_info}"
    
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
        import asyncio
        from telegram import Bot
        
        token = os.getenv('SUPPORT_BOT_TOKEN')
        if not token:
            return
        
        # Получаем всех админов с Telegram ID
        admins = CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False)
        
        if not admins:
            return
        
        priority_emoji = {
            'low': '🟢',
            'normal': '🟡',
            'high': '🟠',
            'urgent': '🔴'
        }.get(self.priority, '⚪')
        
        user_info = self.user.get_full_name() if self.user else self.email or 'Аноним'
        
        message = (
            f"🆕 *Новый тикет #{self.id}*\n\n"
            f"{priority_emoji} *Приоритет:* {self.get_priority_display()}\n"
            f"🏷️ *Категория:* {self.category}\n"
            f"📝 *Тема:* {self.subject}\n"
            f"📄 *Описание:*\n{self.description[:200]}{'...' if len(self.description) > 200 else ''}\n\n"
            f"👤 *От:* {user_info}\n\n"
            f"Для просмотра: /view\\_{self.id}"
        )
        
        bot = Bot(token=token)
        
        for admin in admins:
            try:
                # Используем синхронную версию
                import requests
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    'chat_id': admin.telegram_id,
                    'text': message,
                    'parse_mode': 'Markdown'
                }
                requests.post(url, json=data, timeout=5)
            except Exception as e:
                print(f"Не удалось отправить уведомление админу {admin.id}: {e}")


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
