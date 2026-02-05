"""
ActionExecutor — выполнение автоматических действий

Отвечает за:
- Поиск и загрузку обработчика действия
- Выполнение действия с параметрами
- Логирование результатов
- Проверку лимитов
"""

import logging
import importlib
from typing import Optional
from django.utils import timezone
from django.db.models import Count
from asgiref.sync import sync_to_async

from ..models import ActionDefinition, ActionExecution, Conversation, Message

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Исполнитель автоматических действий.
    
    Пример использования:
    
        result = await ActionExecutor.execute(
            action_name='check_zoom_status',
            conversation=conversation,
            trigger_message=message,
            params={'user_id': user.id},
        )
        
        # result = {
        #     'success': True,
        #     'message': 'Все Zoom-аккаунты работают нормально',
        #     'data': {...},
        # }
    """
    
    @classmethod
    async def execute(
        cls,
        action_name: str,
        conversation: Conversation,
        trigger_message: Optional[Message] = None,
        params: dict = None,
    ) -> dict:
        """
        Выполнить действие.
        
        Args:
            action_name: Системное имя действия
            conversation: Диалог, в котором вызвано действие
            trigger_message: Сообщение, вызвавшее действие
            params: Параметры для действия
        
        Returns:
            dict: Результат выполнения
            {
                'success': bool,
                'message': str,  # Человекочитаемый результат
                'data': dict,    # Данные для AI
                'error': str,    # Ошибка (если есть)
            }
        """
        params = params or {}
        
        # 1. Получаем определение действия
        try:
            action_def = await sync_to_async(
                ActionDefinition.objects.get
            )(name=action_name, is_active=True)
        except ActionDefinition.DoesNotExist:
            logger.error(f"Action not found: {action_name}")
            return {
                'success': False,
                'message': 'Действие не найдено',
                'error': f'Unknown action: {action_name}',
            }
        
        # 2. Проверяем лимиты
        limit_ok = await cls._check_rate_limit(action_def, conversation.user)
        if not limit_ok:
            return {
                'success': False,
                'message': 'Превышен лимит выполнения этого действия. Попробуйте позже.',
                'error': 'Rate limit exceeded',
            }
        
        # 3. Создаём запись о выполнении
        execution = await sync_to_async(ActionExecution.objects.create)(
            action=action_def,
            conversation=conversation,
            triggered_by_message=trigger_message,
            status=ActionExecution.Status.RUNNING,
            input_params=params,
        )
        
        # 4. Загружаем и выполняем обработчик
        try:
            handler = cls._load_handler(action_def.handler_path)
            
            # Добавляем контекст в параметры
            params['_user'] = conversation.user
            params['_conversation'] = conversation
            
            result = await handler(params)
            
            # 5. Сохраняем успешный результат
            execution.status = ActionExecution.Status.SUCCESS
            execution.result = result.get('data', {})
            execution.result_message = result.get('message', '')
            execution.completed_at = timezone.now()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            await sync_to_async(execution.save)()
            
            logger.info(f"Action {action_name} executed successfully for conversation {conversation.id}")
            
            return result
            
        except Exception as e:
            # 6. Сохраняем ошибку
            execution.status = ActionExecution.Status.FAILED
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            await sync_to_async(execution.save)()
            
            logger.error(f"Action {action_name} failed: {e}")
            
            return {
                'success': False,
                'message': 'Произошла ошибка при выполнении действия',
                'error': str(e),
            }
    
    @classmethod
    async def get_available_actions(cls, conversation: Conversation) -> list:
        """
        Получить список доступных действий для диалога.
        
        Args:
            conversation: Диалог
        
        Returns:
            list: Список действий с метаданными
        """
        actions = await sync_to_async(list)(
            ActionDefinition.objects.filter(is_active=True).values(
                'name', 'display_name', 'description', 'category', 'is_read_only'
            )
        )
        return actions
    
    # =========================================================================
    # Private methods
    # =========================================================================
    
    @classmethod
    def _load_handler(cls, handler_path: str):
        """
        Загрузить обработчик по пути.
        
        Args:
            handler_path: Путь вида 'concierge.actions.check_zoom'
        
        Returns:
            Callable: Async функция-обработчик
        """
        module_path, func_name = handler_path.rsplit('.', 1)
        
        # По умолчанию ищем функцию 'execute'
        if not func_name or func_name == module_path.split('.')[-1]:
            func_name = 'execute'
            module_path = handler_path
        
        module = importlib.import_module(module_path)
        handler = getattr(module, func_name)
        
        return handler
    
    @classmethod
    async def _check_rate_limit(cls, action_def: ActionDefinition, user) -> bool:
        """
        Проверить, не превышен ли лимит выполнения.
        
        Args:
            action_def: Определение действия
            user: Пользователь
        
        Returns:
            bool: True если можно выполнять
        """
        if action_def.max_daily_runs_per_user <= 0:
            return True  # Нет лимита
        
        # Считаем выполнения за сегодня
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        count = await sync_to_async(
            ActionExecution.objects.filter(
                action=action_def,
                conversation__user=user,
                started_at__gte=today_start,
            ).count
        )()
        
        return count < action_def.max_daily_runs_per_user
