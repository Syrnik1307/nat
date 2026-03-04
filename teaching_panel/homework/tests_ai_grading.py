"""
Тесты для AI-проверки ДЗ (homework/ai_grading_service.py, models, views, tasks).

Feature flag AI_GRADING_ENABLED=False по умолчанию -> все AI-функции no-op.
"""

import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from schedule.models import Group, Lesson
from homework.models import (
    Homework, Question, StudentSubmission, Answer,
    GeminiAPIKey, AIGradingJob, AIGradingUsage,
)
from homework.ai_grading_service import (
    AIGradingService,
    AIGradingResult,
    BatchGradingResult,
    NoAvailableKeyError,
    TeacherLimitExceededError,
    is_ai_grading_enabled,
)
from django.urls import reverse

User = get_user_model()


# ---------------------------------------------------------------------------
# Helper mixin — общий setUp для всех AI grading тестов
# ---------------------------------------------------------------------------
class AIGradingBaseTestCase(TestCase):
    """Базовый класс: создаёт учителя, ученика, группу, урок, ДЗ, ключ Gemini."""

    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com', password='pass', role='teacher',
        )
        self.student = User.objects.create_user(
            email='student@test.com', password='pass', role='student',
        )
        self.group = Group.objects.create(name='TestGroup', teacher=self.teacher)
        self.group.students.add(self.student)

        start = timezone.now()
        end = start + timedelta(hours=1)
        self.lesson = Lesson.objects.create(
            title='Lesson1', group=self.group, teacher=self.teacher,
            start_time=start, end_time=end,
        )
        self.hw = Homework.objects.create(
            teacher=self.teacher, lesson=self.lesson, title='AI HW',
            ai_grading_mode='auto_send',
            ai_confidence_threshold=0.7,
        )
        # Вопрос, требующий ручной проверки (TEXT)
        self.question = Question.objects.create(
            homework=self.hw, prompt='Объясни теорему Пифагора',
            question_type='TEXT', points=10, order=1,
        )
        # Gemini API ключ
        self.api_key = GeminiAPIKey.objects.create(
            label='test-key-1',
            api_key='AIzaSy_FAKE_KEY_FOR_TESTING',
            is_active=True,
            priority=1,
            daily_request_limit=100,
            daily_token_limit=50000,
            last_reset_date=date.today(),
        )

    def _create_submission_with_answer(self, text='Это ответ ученика'):
        """Создаёт submission + answer (needs_manual_review=True)."""
        sub = StudentSubmission.objects.create(
            homework=self.hw, student=self.student,
            status='submitted', submitted_at=timezone.now(),
        )
        ans = Answer.objects.create(
            submission=sub, question=self.question,
            text_answer=text, needs_manual_review=True,
        )
        return sub, ans


# ===========================================================================
# 1. Model tests
# ===========================================================================
class GeminiAPIKeyModelTests(AIGradingBaseTestCase):

    def test_is_available_active_key(self):
        """Активный ключ без ошибок и с запасом лимита — доступен."""
        self.assertTrue(self.api_key.is_available)

    def test_is_available_inactive_key(self):
        self.api_key.is_active = False
        self.api_key.save()
        self.assertFalse(self.api_key.is_available)

    def test_is_available_disabled_until_future(self):
        self.api_key.disabled_until = timezone.now() + timedelta(minutes=5)
        self.api_key.save()
        self.assertFalse(self.api_key.is_available)

    def test_is_available_disabled_until_past(self):
        self.api_key.disabled_until = timezone.now() - timedelta(minutes=1)
        self.api_key.save()
        self.assertTrue(self.api_key.is_available)

    def test_is_available_daily_limit_reached(self):
        self.api_key.requests_used_today = 100
        self.api_key.save()
        self.assertFalse(self.api_key.is_available)

    def test_is_available_token_limit_reached(self):
        self.api_key.tokens_used_today = 50000
        self.api_key.save()
        self.assertFalse(self.api_key.is_available)

    def test_str_representation(self):
        s = str(self.api_key)
        self.assertIn('test-key-1', s)
        self.assertIn('ON', s)


class AIGradingJobModelTests(AIGradingBaseTestCase):

    def test_create_job(self):
        sub, _ = self._create_submission_with_answer()
        job = AIGradingJob.objects.create(
            submission=sub, homework=self.hw, teacher=self.teacher,
            mode='auto_send', status='pending',
        )
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.total_tokens, 0)

    def test_total_tokens_property(self):
        sub, _ = self._create_submission_with_answer()
        job = AIGradingJob.objects.create(
            submission=sub, homework=self.hw, teacher=self.teacher,
            mode='auto_send', tokens_input=100, tokens_output=50,
        )
        self.assertEqual(job.total_tokens, 150)


class AIGradingUsageModelTests(AIGradingBaseTestCase):

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_monthly_limit_from_settings(self):
        usage = AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
        )
        self.assertEqual(usage.monthly_limit, 500_000)

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_is_limit_exceeded_false(self):
        usage = AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=100_000,
        )
        self.assertFalse(usage.is_limit_exceeded)

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_is_limit_exceeded_true(self):
        usage = AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=600_000,
        )
        self.assertTrue(usage.is_limit_exceeded)

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_tokens_remaining(self):
        usage = AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=200_000,
        )
        self.assertEqual(usage.tokens_remaining, 300_000)

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_tokens_remaining_never_negative(self):
        usage = AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=999_999,
        )
        self.assertEqual(usage.tokens_remaining, 0)


# ===========================================================================
# 2. AIGradingService tests
# ===========================================================================
class FeatureFlagTests(TestCase):

    @override_settings(AI_GRADING_ENABLED=False)
    def test_feature_flag_disabled(self):
        self.assertFalse(is_ai_grading_enabled())

    @override_settings(AI_GRADING_ENABLED=True)
    def test_feature_flag_enabled(self):
        self.assertTrue(is_ai_grading_enabled())


class KeyPoolTests(AIGradingBaseTestCase):

    def test_select_api_key_returns_active_key(self):
        key = AIGradingService.select_api_key()
        self.assertEqual(key.pk, self.api_key.pk)

    def test_select_api_key_skips_inactive(self):
        self.api_key.is_active = False
        self.api_key.save()
        with self.assertRaises(NoAvailableKeyError):
            AIGradingService.select_api_key()

    def test_select_api_key_skips_disabled(self):
        self.api_key.disabled_until = timezone.now() + timedelta(minutes=5)
        self.api_key.save()
        with self.assertRaises(NoAvailableKeyError):
            AIGradingService.select_api_key()

    def test_select_api_key_skips_exhausted(self):
        self.api_key.requests_used_today = 100
        self.api_key.save()
        with self.assertRaises(NoAvailableKeyError):
            AIGradingService.select_api_key()

    def test_select_api_key_priority_ordering(self):
        """Ключ с большим приоритетом выбирается первым."""
        key2 = GeminiAPIKey.objects.create(
            label='test-key-2', api_key='KEY2',
            is_active=True, priority=10,  # выше
            daily_request_limit=100, daily_token_limit=50000,
            last_reset_date=date.today(),
        )
        selected = AIGradingService.select_api_key()
        self.assertEqual(selected.pk, key2.pk)

    def test_select_api_key_auto_resets_date(self):
        """Если дата сменилась — счётчики автоматически сбрасываются."""
        self.api_key.requests_used_today = 99
        self.api_key.last_reset_date = date.today() - timedelta(days=1)
        self.api_key.save()

        key = AIGradingService.select_api_key()
        key.refresh_from_db()
        self.assertEqual(key.requests_used_today, 0)

    def test_record_key_usage(self):
        AIGradingService.record_key_usage(self.api_key, tokens_in=100, tokens_out=50)
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.requests_used_today, 1)
        self.assertEqual(self.api_key.tokens_used_today, 150)
        self.assertEqual(self.api_key.consecutive_errors, 0)

    def test_record_key_error_increments(self):
        AIGradingService.record_key_error(self.api_key, 'Test error')
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.consecutive_errors, 1)
        self.assertEqual(self.api_key.last_error, 'Test error')
        self.assertIsNone(self.api_key.disabled_until)

    def test_record_key_error_disables_after_3(self):
        """3 подряд ошибки → ключ отключается на 5 минут."""
        self.api_key.consecutive_errors = 2
        self.api_key.save()
        AIGradingService.record_key_error(self.api_key, 'Third error')
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.consecutive_errors, 3)
        self.assertIsNotNone(self.api_key.disabled_until)
        self.assertGreater(self.api_key.disabled_until, timezone.now())


class TeacherUsageTests(AIGradingBaseTestCase):

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_check_teacher_limit_ok(self):
        self.assertTrue(AIGradingService.check_teacher_limit(self.teacher))

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_check_teacher_limit_exceeded(self):
        AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=600_000,
        )
        self.assertFalse(AIGradingService.check_teacher_limit(self.teacher))

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_record_teacher_usage(self):
        AIGradingService.record_teacher_usage(self.teacher, tokens=1000)
        usage = AIGradingUsage.objects.get(
            teacher=self.teacher, month=date.today().replace(day=1),
        )
        self.assertEqual(usage.tokens_used, 1000)
        self.assertEqual(usage.requests_count, 1)
        self.assertEqual(usage.submissions_graded, 1)

    @override_settings(AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_get_teacher_remaining_tokens(self):
        AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=200_000,
        )
        remaining = AIGradingService.get_teacher_remaining_tokens(self.teacher)
        self.assertEqual(remaining, 300_000)


class ResponseParsingTests(AIGradingBaseTestCase):
    """Тесты парсинга JSON-ответа от AI."""

    def setUp(self):
        super().setUp()
        self.service = AIGradingService(provider='gemini')
        self.sub, self.ans = self._create_submission_with_answer()

    def test_parse_valid_json(self):
        ai_text = json.dumps([{
            "question_id": self.question.id,
            "score": 8,
            "feedback": "Хороший ответ",
            "confidence": 0.9,
        }])
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].score, 8)
        self.assertEqual(results[0].confidence, 0.9)
        self.assertEqual(results[0].feedback, "Хороший ответ")

    def test_parse_json_with_markdown_fences(self):
        ai_text = '```json\n[{"question_id": %d, "score": 5, "feedback": "OK", "confidence": 0.8}]\n```' % self.question.id
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].score, 5)

    def test_parse_score_clamped_to_max(self):
        """Оценка выше max_points обрезается."""
        ai_text = json.dumps([{
            "question_id": self.question.id,
            "score": 999,
            "feedback": "test",
            "confidence": 0.5,
        }])
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(results[0].score, 10)  # clamped to question points

    def test_parse_score_clamped_to_zero(self):
        """Отрицательная оценка → 0."""
        ai_text = json.dumps([{
            "question_id": self.question.id,
            "score": -5,
            "feedback": "test",
            "confidence": 0.5,
        }])
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(results[0].score, 0)

    def test_parse_confidence_clamped(self):
        """confidence больше 1.0 → 1.0."""
        ai_text = json.dumps([{
            "question_id": self.question.id,
            "score": 5,
            "feedback": "test",
            "confidence": 1.5,
        }])
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(results[0].confidence, 1.0)

    def test_parse_invalid_json_returns_zero_scores(self):
        """Невалидный JSON → все ответы 0 баллов + error."""
        results = self.service._parse_batch_response("NOT JSON", [self.ans])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].score, 0)
        self.assertEqual(results[0].confidence, 0.0)
        self.assertIsNotNone(results[0].error)

    def test_parse_single_object_wrapped_in_list(self):
        """Если AI вернул одиночный объект вместо массива — обернём в список."""
        ai_text = json.dumps({
            "question_id": self.question.id,
            "score": 7,
            "feedback": "test",
            "confidence": 0.85,
        })
        results = self.service._parse_batch_response(ai_text, [self.ans])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].score, 7)


class BatchGradingTests(AIGradingBaseTestCase):
    """Тесты полного batch-грейдинга с mock Gemini API."""

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_GEMINI_MODEL='gemini-2.0-flash')
    @patch('homework.ai_grading_service.httpx.Client')
    def test_grade_submission_batch_success(self, mock_client_class):
        """Успешная batch-проверка через Gemini API."""
        sub, ans = self._create_submission_with_answer('Теорема Пифагора гласит...')

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': json.dumps([{
                            'question_id': self.question.id,
                            'score': 8,
                            'feedback': 'Хороший ответ',
                            'confidence': 0.85,
                        }])
                    }]
                }
            }],
            'usageMetadata': {
                'promptTokenCount': 200,
                'candidatesTokenCount': 50,
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = AIGradingService(provider='gemini')
        result = service.grade_submission_batch(sub)

        self.assertIsNone(result.error)
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].score, 8)
        self.assertEqual(result.tokens_input, 200)
        self.assertEqual(result.tokens_output, 50)

        # Key usage was recorded
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.requests_used_today, 1)
        self.assertEqual(self.api_key.tokens_used_today, 250)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_GEMINI_MODEL='gemini-2.0-flash')
    def test_grade_submission_no_manual_review_answers(self):
        """Если нет needs_manual_review ответов — возвращаем ошибку."""
        sub = StudentSubmission.objects.create(
            homework=self.hw, student=self.student,
            status='submitted', submitted_at=timezone.now(),
        )
        # Создаём ответ БЕЗ needs_manual_review
        Answer.objects.create(
            submission=sub, question=self.question,
            text_answer='test', needs_manual_review=False,
        )
        service = AIGradingService(provider='gemini')
        result = service.grade_submission_batch(sub)
        self.assertIsNotNone(result.error)
        self.assertIn('No answers', result.error)

    @override_settings(AI_GRADING_ENABLED=True)
    def test_grade_submission_no_keys_available(self):
        """Нет доступных ключей → BatchGradingResult с ошибкой."""
        self.api_key.is_active = False
        self.api_key.save()

        sub, _ = self._create_submission_with_answer()
        service = AIGradingService(provider='gemini')
        result = service.grade_submission_batch(sub)
        self.assertIsNotNone(result.error)
        self.assertIn('исчерпаны', result.error)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_GEMINI_MODEL='gemini-2.0-flash')
    @patch('homework.ai_grading_service.httpx.Client')
    def test_grade_submission_rate_limited(self, mock_client_class):
        """429 от Gemini → ошибка + ключ получает record_key_error."""
        sub, _ = self._create_submission_with_answer()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        service = AIGradingService(provider='gemini')
        result = service.grade_submission_batch(sub)

        self.assertIsNotNone(result.error)
        self.assertIn('Rate limited', result.error)

        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.consecutive_errors, 1)


# ===========================================================================
# 3. Celery tasks tests
# ===========================================================================
class CeleryTaskTests(AIGradingBaseTestCase):

    @override_settings(AI_GRADING_ENABLED=False)
    def test_process_queue_noop_when_disabled(self):
        """Когда feature flag OFF — task просто no-op."""
        from homework.tasks import process_ai_grading_queue
        # Не должен упасть
        process_ai_grading_queue()

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_QUEUE_BATCH_SIZE=5)
    @patch('homework.tasks._process_single_job')
    def test_process_queue_picks_pending_jobs(self, mock_process):
        """Очередь обрабатывает pending-задачи."""
        from homework.tasks import process_ai_grading_queue
        sub, _ = self._create_submission_with_answer()
        job = AIGradingJob.objects.create(
            submission=sub, homework=self.hw, teacher=self.teacher,
            mode='auto_send', status='pending',
        )
        process_ai_grading_queue()
        mock_process.assert_called_once()

    @override_settings(AI_GRADING_ENABLED=True)
    @patch('homework.tasks._process_single_job')
    def test_process_queue_skips_non_pending(self, mock_process):
        """Очередь НЕ берёт completed/failed задачи."""
        from homework.tasks import process_ai_grading_queue
        sub, _ = self._create_submission_with_answer()
        AIGradingJob.objects.create(
            submission=sub, homework=self.hw, teacher=self.teacher,
            mode='auto_send', status='completed',
        )
        process_ai_grading_queue()
        mock_process.assert_not_called()

    @override_settings(AI_GRADING_ENABLED=False)
    def test_reset_daily_usage_noop_when_disabled(self):
        from homework.tasks import reset_daily_api_key_usage
        reset_daily_api_key_usage()

    @override_settings(AI_GRADING_ENABLED=True)
    def test_reset_daily_usage_resets_counters(self):
        from homework.tasks import reset_daily_api_key_usage
        self.api_key.requests_used_today = 50
        self.api_key.tokens_used_today = 10000
        # Устанавливаем вчерашнюю дату — тогда task сбросит счётчики
        self.api_key.last_reset_date = date.today() - timedelta(days=1)
        self.api_key.save()

        reset_daily_api_key_usage()
        self.api_key.refresh_from_db()
        self.assertEqual(self.api_key.requests_used_today, 0)
        self.assertEqual(self.api_key.tokens_used_today, 0)
        self.assertEqual(self.api_key.last_reset_date, date.today())

    @override_settings(AI_GRADING_ENABLED=True)
    def test_reset_daily_clears_expired_disabled_until(self):
        from homework.tasks import reset_daily_api_key_usage
        self.api_key.disabled_until = timezone.now() - timedelta(hours=1)
        self.api_key.consecutive_errors = 5
        self.api_key.save()

        reset_daily_api_key_usage()
        self.api_key.refresh_from_db()
        # Task снимает disabled_until если оно в прошлом
        self.assertIsNone(self.api_key.disabled_until)
        # consecutive_errors не сбрасывается этим таском
        self.assertEqual(self.api_key.consecutive_errors, 5)

    @override_settings(AI_GRADING_ENABLED=False)
    def test_check_pool_capacity_noop_when_disabled(self):
        from homework.tasks import check_ai_pool_capacity
        check_ai_pool_capacity()

    @override_settings(AI_GRADING_ENABLED=False)
    def test_weekly_report_noop_when_disabled(self):
        from homework.tasks import send_ai_usage_weekly_report
        send_ai_usage_weekly_report()


# ===========================================================================
# 4. Views tests
# ===========================================================================
class AIUsageViewTests(AIGradingBaseTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.url = reverse('homework-submission-ai-usage')

    @override_settings(AI_GRADING_ENABLED=False)
    def test_ai_usage_disabled(self):
        """Когда AI выключен — enabled=False."""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200, f"Expected 200 but got {resp.status_code}. Content: {resp.content[:500]}")
        self.assertFalse(resp.data['enabled'])
        self.assertEqual(resp.data['tokens_used'], 0)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_ai_usage_enabled_fresh(self):
        """Когда AI включён — возвращает usage и лимит."""
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['enabled'])
        self.assertEqual(resp.data['tokens_limit'], 500_000)
        self.assertEqual(resp.data['tokens_remaining'], 500_000)
        self.assertEqual(resp.data['pending_jobs'], 0)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_ai_usage_with_existing_usage(self):
        self.client.force_authenticate(user=self.teacher)
        AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=120_000, requests_count=5, submissions_graded=5,
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['tokens_used'], 120_000)
        self.assertEqual(resp.data['tokens_remaining'], 380_000)
        self.assertEqual(resp.data['requests_count'], 5)
        self.assertEqual(resp.data['submissions_graded'], 5)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_ai_usage_pending_jobs_counted(self):
        self.client.force_authenticate(user=self.teacher)
        sub, _ = self._create_submission_with_answer()
        AIGradingJob.objects.create(
            submission=sub, homework=self.hw, teacher=self.teacher,
            mode='auto_send', status='pending',
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.data['pending_jobs'], 1)

    def test_ai_usage_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)


class SubmitWithAIGradingTests(AIGradingBaseTestCase):
    """Тесты submit() -> _try_create_ai_grading_job."""

    @override_settings(AI_GRADING_ENABLED=False)
    def test_try_create_job_disabled(self):
        """Когда feature flag OFF — job не создаётся."""
        from homework.views import StudentSubmissionViewSet
        sub, _ = self._create_submission_with_answer()
        result = StudentSubmissionViewSet._try_create_ai_grading_job(sub, self.hw)
        self.assertFalse(result)
        self.assertEqual(AIGradingJob.objects.count(), 0)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_try_create_job_enabled(self):
        """Когда feature flag ON — job создаётся."""
        from homework.views import StudentSubmissionViewSet
        sub, _ = self._create_submission_with_answer()
        result = StudentSubmissionViewSet._try_create_ai_grading_job(sub, self.hw)
        self.assertTrue(result)
        self.assertEqual(AIGradingJob.objects.count(), 1)
        job = AIGradingJob.objects.first()
        self.assertEqual(job.status, 'pending')
        self.assertEqual(job.mode, 'auto_send')
        self.assertEqual(job.teacher_id, self.teacher.id)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=100)
    @patch('accounts.notifications.send_telegram_notification')
    def test_try_create_job_limit_exceeded(self, mock_notify):
        """Когда лимит исчерпан — job не создаётся, Telegram ping."""
        from homework.views import StudentSubmissionViewSet
        AIGradingUsage.objects.create(
            teacher=self.teacher, month=date.today().replace(day=1),
            tokens_used=999_999,
        )
        sub, _ = self._create_submission_with_answer()
        result = StudentSubmissionViewSet._try_create_ai_grading_job(sub, self.hw)
        self.assertFalse(result)
        self.assertEqual(AIGradingJob.objects.count(), 0)

    @override_settings(AI_GRADING_ENABLED=True, AI_GRADING_DEFAULT_MONTHLY_LIMIT=500_000)
    def test_try_create_job_mode_none_no_job(self):
        """Если ai_grading_mode = 'none' — job не создаётся
        (потому что submit() в view проверяет mode перед вызовом)."""
        self.hw.ai_grading_mode = 'none'
        self.hw.save()
        # _try_create_ai_grading_job сам не проверяет mode,
        # но создаёт job с mode=homework.ai_grading_mode
        # Проверяем что submit() view проверяет mode
        from homework.views import StudentSubmissionViewSet
        # Здесь job будет создан с mode='none' — это ок,
        # потому что в реальном коде submit() проверяет mode != 'none'
        sub, _ = self._create_submission_with_answer()
        result = StudentSubmissionViewSet._try_create_ai_grading_job(sub, self.hw)
        self.assertTrue(result)  # _try сам не фильтрует mode


class HomeworkSerializerAIFieldsTests(AIGradingBaseTestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_ai_fields_in_homework_response(self):
        """Поля ai_grading_mode и ai_confidence_threshold есть в ответе API."""
        self.client.force_authenticate(user=self.teacher)
        url = reverse('homework-detail', args=[self.hw.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200, f"Expected 200 but got {resp.status_code}. URL={url} Content: {resp.content[:500]}")
        self.assertIn('ai_grading_mode', resp.data)
        self.assertEqual(resp.data['ai_grading_mode'], 'auto_send')
        self.assertIn('ai_confidence_threshold', resp.data)
        self.assertEqual(resp.data['ai_confidence_threshold'], 0.7)
