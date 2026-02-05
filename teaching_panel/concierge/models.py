"""
Модели данных для Lectio Concierge

Conversation — диалог с пользователем
Message — сообщение в диалоге (от user/ai/admin/system)
KnowledgeDocument — документ базы знаний
KnowledgeChunk — чанк для RAG-поиска
ActionDefinition — определение автоматического действия
ActionExecution — лог выполнения действия
"""

import uuid
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings


class Conversation(models.Model):
    """
    Диалог в системе поддержки.
    
    Жизненный цикл:
    1. AI_MODE — AI отвечает автоматически
    2. HUMAN_MODE — подключён оператор из Telegram
    3. RESOLVED — проблема решена
    4. CLOSED — диалог закрыт
    """
    
    class Status(models.TextChoices):
        AI_MODE = 'ai_mode', 'AI отвечает'
        HUMAN_MODE = 'human_mode', 'Подключён оператор'
        RESOLVED = 'resolved', 'Решён'
        CLOSED = 'closed', 'Закрыт'
    
    class Language(models.TextChoices):
        RU = 'ru', 'Русский'
        EN = 'en', 'English'
    
    # UUID для публичных ссылок (не раскрываем auto-increment ID)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    
    # Привязка к пользователю (только авторизованные)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='concierge_conversations',
        verbose_name='Пользователь'
    )
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.AI_MODE,
        db_index=True
    )
    
    language = models.CharField(
        'Язык',
        max_length=5,
        choices=Language.choices,
        default=Language.RU
    )
    
    # Контекст страницы (откуда открыт виджет)
    page_url = models.URLField('URL страницы', blank=True, max_length=500)
    page_title = models.CharField('Название страницы', max_length=200, blank=True)
    
    # Техническая информация о клиенте
    user_agent = models.TextField('User Agent', blank=True)
    client_info = models.JSONField(
        'Информация о клиенте',
        default=dict,
        blank=True,
        help_text='browser, os, screen_resolution, timezone'
    )
    
    # Контекст пользователя (для AI)
    user_context = models.JSONField(
        'Контекст пользователя',
        default=dict,
        blank=True,
        help_text='role, subscription_status, recent_activity'
    )
    
    # Telegram интеграция
    telegram_thread_id = models.BigIntegerField(
        'Telegram Thread ID',
        null=True,
        blank=True,
        db_index=True,
        help_text='ID топика в группе поддержки'
    )
    
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_concierge_conversations',
        verbose_name='Назначенный оператор'
    )
    
    # AI метрики
    ai_messages_count = models.PositiveIntegerField('Сообщений от AI', default=0)
    ai_escalated_at = models.DateTimeField('Время эскалации', null=True, blank=True)
    ai_escalation_reason = models.TextField('Причина эскалации', blank=True)
    ai_retry_count = models.PositiveSmallIntegerField('Попыток AI уточнить', default=0)
    
    # Timestamps
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    resolved_at = models.DateTimeField('Решён', null=True, blank=True)
    last_user_message_at = models.DateTimeField('Последнее сообщение юзера', null=True, blank=True)
    last_admin_message_at = models.DateTimeField('Последнее сообщение оператора', null=True, blank=True)
    
    # Оценка качества
    user_rating = models.PositiveSmallIntegerField(
        'Оценка пользователя',
        null=True,
        blank=True,
        help_text='1-5 звёзд'
    )
    user_feedback = models.TextField('Отзыв пользователя', blank=True)
    
    class Meta:
        verbose_name = 'Диалог'
        verbose_name_plural = 'Диалоги'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"#{self.id} {self.user.email} ({self.get_status_display()})"
    
    def escalate_to_human(self, reason: str = ''):
        """Переключить на оператора"""
        self.status = self.Status.HUMAN_MODE
        self.ai_escalated_at = timezone.now()
        self.ai_escalation_reason = reason
        self.save(update_fields=['status', 'ai_escalated_at', 'ai_escalation_reason', 'updated_at'])
    
    def resolve(self):
        """Отметить как решённый"""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at', 'updated_at'])
    
    def close(self):
        """Закрыть диалог"""
        self.status = self.Status.CLOSED
        self.save(update_fields=['status', 'updated_at'])


class Message(models.Model):
    """
    Сообщение в диалоге.
    
    Типы отправителей:
    - user: пользователь системы
    - ai: AI-агент
    - admin: оператор из Telegram
    - system: системное уведомление
    """
    
    class SenderType(models.TextChoices):
        USER = 'user', 'Пользователь'
        AI = 'ai', 'AI-агент'
        ADMIN = 'admin', 'Оператор'
        SYSTEM = 'system', 'Система'
    
    class ContentType(models.TextChoices):
        TEXT = 'text', 'Текст'
        IMAGE = 'image', 'Изображение'
        VOICE = 'voice', 'Голосовое'
        FILE = 'file', 'Файл'
        ACTION_RESULT = 'action_result', 'Результат действия'
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Диалог'
    )
    
    sender_type = models.CharField(
        'Тип отправителя',
        max_length=10,
        choices=SenderType.choices
    )
    
    sender_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='concierge_messages',
        verbose_name='Отправитель',
        help_text='Заполнено для user/admin'
    )
    
    content_type = models.CharField(
        'Тип контента',
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.TEXT
    )
    
    content = models.TextField('Содержимое')
    
    # Для файлов/изображений
    attachment_url = models.URLField('URL вложения', blank=True, max_length=500)
    attachment_meta = models.JSONField(
        'Метаданные вложения',
        default=dict,
        blank=True,
        help_text='filename, size_bytes, mime_type'
    )
    
    # AI метаданные
    ai_confidence = models.FloatField(
        'Уверенность AI',
        null=True,
        blank=True,
        help_text='0.0 - 1.0'
    )
    ai_sources = models.JSONField(
        'Источники AI',
        default=list,
        blank=True,
        help_text='[{doc_id, chunk_id, score}]'
    )
    ai_model = models.CharField('Модель AI', max_length=50, blank=True)
    ai_tokens_used = models.PositiveIntegerField('Токенов использовано', null=True, blank=True)
    
    # Telegram sync
    telegram_message_id = models.BigIntegerField(
        'Telegram Message ID',
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField('Создано', auto_now_add=True, db_index=True)
    read_at = models.DateTimeField('Прочитано', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.get_sender_type_display()}: {preview}"
    
    def mark_read(self):
        """Отметить как прочитанное"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])


class KnowledgeDocument(models.Model):
    """
    Документ базы знаний.
    
    Источники:
    - Markdown файлы из docs/knowledge/
    - FAQ статьи
    - Инструкции для пользователей
    """
    
    class Category(models.TextChoices):
        FAQ = 'faq', 'FAQ'
        GUIDE = 'guide', 'Инструкция'
        TROUBLESHOOTING = 'troubleshooting', 'Решение проблем'
        FEATURE = 'feature', 'Описание функции'
        POLICY = 'policy', 'Политики и правила'
    
    # Путь к файлу (для автосинхронизации)
    source_path = models.CharField(
        'Путь к файлу',
        max_length=500,
        unique=True,
        help_text='Относительный путь, например: docs/knowledge/faq/payments.md'
    )
    
    title = models.CharField('Заголовок', max_length=200)
    
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=Category.choices,
        default=Category.FAQ
    )
    
    # Для отслеживания изменений
    content_hash = models.CharField(
        'Хеш контента',
        max_length=64,
        help_text='SHA256 для определения изменений'
    )
    
    # Метаданные
    language = models.CharField('Язык', max_length=5, default='ru')
    tags = models.JSONField('Теги', default=list, blank=True)
    
    # Статус индексации
    is_active = models.BooleanField('Активен', default=True)
    last_indexed_at = models.DateTimeField('Последняя индексация', null=True, blank=True)
    indexing_error = models.TextField('Ошибка индексации', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    
    class Meta:
        verbose_name = 'Документ базы знаний'
        verbose_name_plural = 'Документы базы знаний'
        ordering = ['category', 'title']
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """Вычислить хеш контента"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class KnowledgeChunk(models.Model):
    """
    Чанк документа для RAG-поиска.
    
    Документ разбивается на чанки по 300-500 токенов
    для эффективного поиска по embedding'ам.
    """
    
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name='Документ'
    )
    
    chunk_index = models.PositiveIntegerField('Индекс в документе')
    content = models.TextField('Содержимое чанка')
    
    # Контекст чанка (для лучшего понимания)
    section_title = models.CharField('Заголовок секции', max_length=200, blank=True)
    
    # Embedding
    embedding_model = models.CharField(
        'Модель embedding',
        max_length=50,
        default='text-embedding-3-small'
    )
    
    # Для PostgreSQL + pgvector (добавим позже)
    # embedding = VectorField(dimensions=1536, null=True)
    
    # Пока храним как JSON (для разработки)
    embedding_json = models.JSONField(
        'Embedding (JSON)',
        null=True,
        blank=True,
        help_text='Временное хранение, мигрируем на pgvector'
    )
    
    # Метаданные для поиска
    metadata = models.JSONField(
        'Метаданные',
        default=dict,
        blank=True,
        help_text='keywords, entities, importance_score'
    )
    
    # Timestamps
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Чанк базы знаний'
        verbose_name_plural = 'Чанки базы знаний'
        ordering = ['document', 'chunk_index']
        unique_together = ['document', 'chunk_index']
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class ActionDefinition(models.Model):
    """
    Определение автоматического действия.
    
    AI может вызывать эти действия для диагностики
    или автоматического решения проблем.
    """
    
    class Category(models.TextChoices):
        DIAGNOSTIC = 'diagnostic', 'Диагностика'
        FIX = 'fix', 'Исправление'
        INFO = 'info', 'Информация'
    
    name = models.CharField(
        'Системное имя',
        max_length=100,
        unique=True,
        help_text='Например: check_zoom_status'
    )
    
    display_name = models.CharField('Отображаемое имя', max_length=200)
    display_name_en = models.CharField('Имя (EN)', max_length=200, blank=True)
    
    description = models.TextField(
        'Описание',
        help_text='Подробное описание для AI — когда использовать это действие'
    )
    
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=Category.choices,
        default=Category.DIAGNOSTIC
    )
    
    # Путь к handler'у
    handler_path = models.CharField(
        'Путь к обработчику',
        max_length=200,
        help_text='Например: concierge.actions.check_zoom'
    )
    
    # Для AI-классификации
    trigger_keywords = models.JSONField(
        'Ключевые слова',
        default=list,
        help_text='Слова, при которых AI рассмотрит это действие'
    )
    
    trigger_categories = models.JSONField(
        'Категории проблем',
        default=list,
        help_text='zoom, payment, recording, lesson...'
    )
    
    # Параметры
    required_params = models.JSONField(
        'Обязательные параметры',
        default=list,
        help_text='Какие данные нужны для выполнения'
    )
    
    # Безопасность
    is_read_only = models.BooleanField(
        'Только чтение',
        default=True,
        help_text='Не изменяет данные'
    )
    
    requires_confirmation = models.BooleanField(
        'Требует подтверждения',
        default=False,
        help_text='Спросить пользователя перед выполнением'
    )
    
    max_daily_runs_per_user = models.PositiveIntegerField(
        'Лимит в день на пользователя',
        default=10
    )
    
    # Статус
    is_active = models.BooleanField('Активно', default=True)
    
    # Timestamps
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Автоматическое действие'
        verbose_name_plural = 'Автоматические действия'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"


class ActionExecution(models.Model):
    """
    Лог выполнения автоматического действия.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        RUNNING = 'running', 'Выполняется'
        SUCCESS = 'success', 'Успешно'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменено'
    
    action = models.ForeignKey(
        ActionDefinition,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='Действие'
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='action_executions',
        verbose_name='Диалог'
    )
    
    triggered_by_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_actions',
        verbose_name='Триггер-сообщение'
    )
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    input_params = models.JSONField('Входные параметры', default=dict)
    result = models.JSONField('Результат', default=dict, blank=True)
    result_message = models.TextField(
        'Сообщение результата',
        blank=True,
        help_text='Человекочитаемый результат для показа пользователю'
    )
    error_message = models.TextField('Ошибка', blank=True)
    
    # Timing
    started_at = models.DateTimeField('Начало', auto_now_add=True)
    completed_at = models.DateTimeField('Завершение', null=True, blank=True)
    duration_ms = models.PositiveIntegerField('Длительность (мс)', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Выполнение действия'
        verbose_name_plural = 'Выполнения действий'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.action.name} - {self.get_status_display()}"
    
    def complete(self, result: dict, message: str = ''):
        """Отметить как успешно завершённое"""
        self.status = self.Status.SUCCESS
        self.result = result
        self.result_message = message
        self.completed_at = timezone.now()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()
    
    def fail(self, error: str):
        """Отметить как неудачное"""
        self.status = self.Status.FAILED
        self.error_message = error
        self.completed_at = timezone.now()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.save()


class ConversationMetrics(models.Model):
    """
    Агрегированная аналитика по диалогам (для дашборда).
    Обновляется периодически через Celery.
    """
    
    date = models.DateField('Дата', unique=True, db_index=True)
    
    # Количество диалогов
    total_conversations = models.PositiveIntegerField('Всего диалогов', default=0)
    ai_only_resolved = models.PositiveIntegerField('Решено AI', default=0)
    escalated_to_human = models.PositiveIntegerField('Эскалировано', default=0)
    
    # Время ответа
    avg_ai_response_time_ms = models.PositiveIntegerField('Среднее время AI (мс)', default=0)
    avg_human_response_time_sec = models.PositiveIntegerField('Среднее время оператора (сек)', default=0)
    
    # Удовлетворённость
    avg_rating = models.FloatField('Средняя оценка', null=True, blank=True)
    ratings_count = models.PositiveIntegerField('Количество оценок', default=0)
    
    # Действия
    actions_executed = models.PositiveIntegerField('Действий выполнено', default=0)
    actions_success_rate = models.FloatField('Успешность действий (%)', default=0)
    
    # Timestamps
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Метрики диалогов'
        verbose_name_plural = 'Метрики диалогов'
        ordering = ['-date']
    
    def __str__(self):
        return f"Metrics {self.date}"
