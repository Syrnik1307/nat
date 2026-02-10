"""
AI Grading Gateway — прослойка между монолитом и AI-микросервисом.

Решает куда отправить проверку:
- AI_GRADING_ASYNC=1 → Redis Queue (Celery task) → AI Worker → Callback
- AI_GRADING_ASYNC=0 → синхронный вызов через _evaluate_with_ai() (legacy fallback)

Этот модуль — единственная точка входа для AI-проверки из бизнес-логики.
"""

import uuid
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class AIGradingGateway:
    """
    Gateway для отправки ответов на AI-проверку.
    
    Использование:
        gateway = AIGradingGateway()
        job_id = gateway.submit_for_grading(answer, homework)
        # answer.ai_grading_status == 'pending'
        # answer.grading_job_id == job_id
    """

    def submit_for_grading(self, answer, homework) -> Optional[str]:
        """
        Отправляет ответ на AI-проверку.
        
        При AI_GRADING_ASYNC=True — ставит в очередь Celery, возвращает job_id.
        При AI_GRADING_ASYNC=False — вызывает _evaluate_with_ai() синхронно (legacy).
        
        Returns:
            str: grading_job_id (UUID) при async, None при sync
        """
        if not homework.ai_grading_enabled:
            logger.debug(f"AI grading disabled for homework {homework.id}")
            return None

        if settings.AI_GRADING_ASYNC:
            return self._submit_async(answer, homework)
        else:
            return self._submit_sync(answer, homework)

    def _submit_async(self, answer, homework) -> str:
        """Ставит задачу в Redis-очередь через Celery."""
        from homework.tasks import process_ai_grading

        job_id = str(uuid.uuid4())

        # Обновляем статус на Answer
        answer.grading_job_id = job_id
        answer.ai_grading_status = 'pending'
        answer.save(update_fields=['grading_job_id', 'ai_grading_status'])

        # Формируем payload
        q = answer.question
        config = q.config or {}

        # Данные ответа студента
        student_answer_data = {
            'text': answer.text_answer or '',
        }

        # Для CODE — добавляем структурированные данные
        if q.question_type == 'CODE':
            try:
                import json
                answer_data = json.loads(answer.text_answer) if answer.text_answer else {}
                student_answer_data['text'] = answer_data.get('code', answer.text_answer or '')
                student_answer_data['test_results'] = answer_data.get('testResults', [])
                student_answer_data['language'] = config.get('language', '')
            except (json.JSONDecodeError, TypeError):
                pass

        # Для FILE_UPLOAD — добавляем метаданные файлов
        if q.question_type == 'FILE_UPLOAD' and answer.attachments:
            student_answer_data['file_info'] = answer.attachments

        payload = {
            'task_id': f'grade_{job_id}',
            'version': '1',
            'callback_url': settings.AI_CALLBACK_URL,
            'grading_request': {
                'answer_id': answer.id,
                'submission_id': answer.submission_id,
                'homework_id': homework.id,
                'question_type': q.question_type,
                'question': {
                    'prompt': q.prompt,
                    'max_points': q.points,
                    'correct_answer': config.get('correctAnswer', '') or None,
                    'subject_context': homework.ai_grading_prompt or None,
                },
                'student_answer': student_answer_data,
                'grading_config': {
                    'provider': homework.ai_provider or 'deepseek',
                    'custom_prompt': homework.ai_grading_prompt or None,
                    'language': 'ru',
                },
            },
        }

        # Отправляем в Celery
        process_ai_grading.apply_async(
            args=[payload],
            task_id=f'grade_{job_id}',
        )

        logger.info(
            f"AI grading queued: answer={answer.id}, job={job_id}, "
            f"homework={homework.id}, provider={homework.ai_provider}"
        )
        return job_id

    def _submit_sync(self, answer, homework) -> None:
        """Legacy: синхронный вызов AI (блокирующий)."""
        answer._evaluate_with_ai(homework)
        return None

    def submit_batch(self, answers, homework) -> dict:
        """
        Массовая отправка ответов на AI-проверку.
        Поддерживает типы: TEXT, CODE, FILE_UPLOAD.
        
        Returns:
            dict: {'queued': int, 'skipped': int, 'job_ids': list}
        """
        AI_SUPPORTED_TYPES = {'TEXT', 'CODE', 'FILE_UPLOAD'}
        queued = 0
        skipped = 0
        job_ids = []

        for answer in answers:
            if answer.question.question_type not in AI_SUPPORTED_TYPES:
                skipped += 1
                continue
            if answer.auto_score is not None or answer.teacher_score is not None:
                skipped += 1
                continue
            if answer.ai_grading_status in ('pending', 'processing', 'completed'):
                skipped += 1
                continue

            job_id = self.submit_for_grading(answer, homework)
            if job_id:
                queued += 1
                job_ids.append(job_id)
            else:
                skipped += 1

        logger.info(
            f"AI batch grading: homework={homework.id}, "
            f"queued={queued}, skipped={skipped}"
        )
        return {
            'queued': queued,
            'skipped': skipped,
            'job_ids': job_ids,
        }
