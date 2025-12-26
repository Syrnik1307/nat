"""
AI Behavior Analytics Service - анализ поведения студентов

Генерирует отчёты для преподавателей на основе:
- Посещаемости (присутствие, пропуски, опоздания)
- Сдачи ДЗ (вовремя, с опозданием, не сдано)
- Динамики оценок
- Контрольных точек
"""

import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import date, timedelta, datetime

import httpx
from django.conf import settings
from django.db.models import Avg, Count, Q, F
from django.utils import timezone

from accounts.models import AttendanceRecord, CustomUser
from schedule.models import Lesson, Group
from homework.models import Homework, StudentSubmission
from analytics.models import ControlPoint, ControlPointResult, StudentBehaviorReport

logger = logging.getLogger(__name__)


@dataclass
class BehaviorMetrics:
    """Собранные метрики поведения студента"""
    # Посещаемость
    total_lessons: int = 0
    attended_lessons: int = 0
    missed_lessons: int = 0
    late_arrivals: int = 0
    attendance_rate: float = 0.0
    
    # Домашние задания
    total_homework: int = 0
    submitted_on_time: int = 0
    submitted_late: int = 0
    not_submitted: int = 0
    homework_rate: float = 0.0
    
    # Оценки
    avg_score: Optional[float] = None
    score_trend: str = 'stable'
    control_points_count: int = 0
    control_points_avg: Optional[float] = None
    
    # Детали для AI
    lesson_details: List[Dict] = None
    homework_details: List[Dict] = None
    
    def __post_init__(self):
        if self.lesson_details is None:
            self.lesson_details = []
        if self.homework_details is None:
            self.homework_details = []


@dataclass
class AIBehaviorResult:
    """Результат AI анализа поведения"""
    profile_type: str  # responsible, needs_attention, at_risk
    risk_level: str  # low, medium, high
    reliability_score: int  # 0-100
    strengths: List[str]
    concerns: List[str]
    patterns: List[Dict[str, str]]
    recommendations: List[Dict[str, str]]
    alerts: List[Dict[str, str]]
    predicted_completion_probability: int
    summary: str
    confidence: float
    tokens_used: int
    error: Optional[str] = None


class BehaviorAnalyticsService:
    """Сервис AI-аналитики поведения студентов"""
    
    BEHAVIOR_ANALYSIS_PROMPT = """Ты — опытный преподаватель-аналитик, специализирующийся на прогнозировании успеха студентов.
Проанализируй поведение ученика и дай рекомендации.

ДАННЫЕ УЧЕНИКА:
Имя: {student_name}
Группа: {group_name}
Период: {period}

ПОСЕЩАЕМОСТЬ:
- Всего занятий: {total_lessons}
- Посещено: {attended_lessons} ({attendance_rate:.0f}%)
- Пропущено: {missed_lessons}
- Опозданий: {late_arrivals}

ДОМАШНИЕ ЗАДАНИЯ:
- Всего ДЗ: {total_homework}
- Сдано вовремя: {submitted_on_time}
- Сдано с опозданием: {submitted_late}
- Не сдано: {not_submitted}
- Процент сдачи: {homework_rate:.0f}%

УСПЕВАЕМОСТЬ:
- Средний балл: {avg_score}
- Тренд: {score_trend}
- Контрольных точек: {control_points_count}
- Средний балл КТ: {control_points_avg}

ДЕТАЛИ ЗАНЯТИЙ (последние):
{lesson_details}

ДЕТАЛИ ДЗ (последние):
{homework_details}

ЗАДАЧА:
1. Определи тип ученика: "responsible" (ответственный), "needs_attention" (нужен контроль), "at_risk" (риск ухода)
2. Оцени уровень риска: "low", "medium", "high"
3. Дай балл надёжности 0-100 (насколько можно положиться на ученика)
4. Выяви паттерны поведения (например, пропускает по определённым дням)
5. Дай конкретные рекомендации учителю

ВАЖНО:
- Будь конкретным и практичным
- Если есть тревожные сигналы — обязательно укажи
- Рекомендации должны быть actionable

Ответь СТРОГО в формате JSON:
{{
    "profile_type": "responsible|needs_attention|at_risk",
    "risk_level": "low|medium|high",
    "reliability_score": 85,
    "strengths": ["Сильная сторона 1", "Сильная сторона 2"],
    "concerns": ["Проблема 1", "Проблема 2"],
    "patterns": [
        {{"type": "attendance|homework|grades", "description": "Описание паттерна"}}
    ],
    "recommendations": [
        {{"priority": "high|medium|low", "action": "Конкретное действие для учителя"}}
    ],
    "alerts": [
        {{"type": "warning|info", "message": "Важное уведомление для учителя"}}
    ],
    "predicted_completion_probability": 75,
    "summary": "2-3 предложения с общим выводом о поведении ученика"
}}"""

    def __init__(self, provider: str = 'deepseek'):
        self.provider = provider
        self.timeout = 60
        
    def _get_api_config(self) -> tuple:
        """Возвращает (api_url, api_key, model) для провайдера"""
        if self.provider == 'deepseek':
            return (
                'https://api.deepseek.com/v1/chat/completions',
                getattr(settings, 'DEEPSEEK_API_KEY', ''),
                'deepseek-chat'
            )
        elif self.provider == 'openai':
            return (
                'https://api.openai.com/v1/chat/completions',
                getattr(settings, 'OPENAI_API_KEY', ''),
                'gpt-4o-mini'
            )
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def collect_metrics(
        self,
        student: CustomUser,
        group: Optional[Group] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> BehaviorMetrics:
        """Собирает метрики поведения студента"""
        
        # Дефолтный период — последние 30 дней
        if not period_end:
            period_end = timezone.now().date()
        if not period_start:
            period_start = period_end - timedelta(days=30)
        
        metrics = BehaviorMetrics()
        
        # ===== ПОСЕЩАЕМОСТЬ =====
        attendance_qs = AttendanceRecord.objects.filter(
            student=student,
            lesson__start_time__date__gte=period_start,
            lesson__start_time__date__lte=period_end
        )
        
        if group:
            attendance_qs = attendance_qs.filter(lesson__group=group)
        
        attendance_qs = attendance_qs.select_related('lesson')
        
        for record in attendance_qs:
            metrics.total_lessons += 1
            if record.status == AttendanceRecord.STATUS_ATTENDED:
                metrics.attended_lessons += 1
            elif record.status == AttendanceRecord.STATUS_ABSENT:
                metrics.missed_lessons += 1
            elif record.status == AttendanceRecord.STATUS_WATCHED_RECORDING:
                # Посмотрел запись — считаем как "частичное" посещение
                metrics.attended_lessons += 1
            
            # Детали для AI
            metrics.lesson_details.append({
                'date': record.lesson.start_time.strftime('%d.%m.%Y'),
                'title': record.lesson.title or 'Занятие',
                'status': record.get_status_display() if record.status else 'Не отмечено',
            })
        
        # Считаем опоздания (если есть данные о времени подключения)
        # TODO: Добавить поле join_time в AttendanceRecord для трекинга опозданий
        
        if metrics.total_lessons > 0:
            metrics.attendance_rate = (metrics.attended_lessons / metrics.total_lessons) * 100
        
        # ===== ДОМАШНИЕ ЗАДАНИЯ =====
        # Находим ДЗ для группы
        homework_qs = Homework.objects.filter(
            status='published',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        
        if group:
            homework_qs = homework_qs.filter(lesson__group=group)
        
        for hw in homework_qs:
            metrics.total_homework += 1
            
            # Проверяем сдачу студентом
            submission = StudentSubmission.objects.filter(
                homework=hw,
                student=student
            ).first()
            
            hw_detail = {
                'title': hw.title,
                'created': hw.created_at.strftime('%d.%m.%Y'),
            }
            
            if submission:
                if submission.status == 'submitted' or submission.status == 'graded':
                    # Проверяем, вовремя ли сдано
                    # TODO: Добавить deadline поле в Homework
                    metrics.submitted_on_time += 1
                    hw_detail['status'] = 'Сдано'
                    hw_detail['score'] = submission.total_score
                else:
                    metrics.submitted_late += 1
                    hw_detail['status'] = 'В процессе'
            else:
                metrics.not_submitted += 1
                hw_detail['status'] = 'Не сдано'
            
            metrics.homework_details.append(hw_detail)
        
        if metrics.total_homework > 0:
            submitted = metrics.submitted_on_time + metrics.submitted_late
            metrics.homework_rate = (submitted / metrics.total_homework) * 100
        
        # ===== ОЦЕНКИ =====
        # Средний балл по ДЗ
        avg_result = StudentSubmission.objects.filter(
            student=student,
            status='graded',
            graded_at__date__gte=period_start,
            graded_at__date__lte=period_end
        ).aggregate(avg=Avg('total_score'))
        
        metrics.avg_score = avg_result['avg']
        
        # Контрольные точки
        if group:
            cp_results = ControlPointResult.objects.filter(
                student=student,
                control_point__group=group,
                control_point__date__gte=period_start,
                control_point__date__lte=period_end
            ).select_related('control_point')
            
            metrics.control_points_count = cp_results.count()
            
            if metrics.control_points_count > 0:
                cp_avg = cp_results.aggregate(avg=Avg('points'))
                metrics.control_points_avg = cp_avg['avg']
        
        # Тренд оценок (сравнение первой и второй половины периода)
        mid_date = period_start + (period_end - period_start) / 2
        
        first_half = StudentSubmission.objects.filter(
            student=student,
            status='graded',
            graded_at__date__gte=period_start,
            graded_at__date__lt=mid_date
        ).aggregate(avg=Avg('total_score'))
        
        second_half = StudentSubmission.objects.filter(
            student=student,
            status='graded',
            graded_at__date__gte=mid_date,
            graded_at__date__lte=period_end
        ).aggregate(avg=Avg('total_score'))
        
        if first_half['avg'] and second_half['avg']:
            diff = second_half['avg'] - first_half['avg']
            if diff > 5:
                metrics.score_trend = 'improving'
            elif diff < -5:
                metrics.score_trend = 'declining'
            else:
                metrics.score_trend = 'stable'
        
        return metrics

    def generate_report(
        self,
        student: CustomUser,
        teacher: CustomUser,
        group: Optional[Group] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> StudentBehaviorReport:
        """Генерирует полный отчёт о поведении студента"""
        
        # Дефолтный период
        if not period_end:
            period_end = timezone.now().date()
        if not period_start:
            period_start = period_end - timedelta(days=30)
        
        # Проверяем существующий отчёт
        existing = StudentBehaviorReport.objects.filter(
            student=student,
            teacher=teacher,
            group=group,
            period_start=period_start,
            period_end=period_end
        ).first()
        
        if existing and existing.status == 'completed':
            # Отдаём существующий, если создан менее 24 часов назад
            if (timezone.now() - existing.updated_at).total_seconds() < 86400:
                return existing
        
        # Создаём или обновляем отчёт
        report, created = StudentBehaviorReport.objects.update_or_create(
            student=student,
            teacher=teacher,
            group=group,
            period_start=period_start,
            period_end=period_end,
            defaults={'status': 'generating'}
        )
        
        try:
            # Собираем метрики
            metrics = self.collect_metrics(student, group, period_start, period_end)
            
            # Сохраняем метрики
            report.total_lessons = metrics.total_lessons
            report.attended_lessons = metrics.attended_lessons
            report.missed_lessons = metrics.missed_lessons
            report.late_arrivals = metrics.late_arrivals
            report.attendance_rate = metrics.attendance_rate
            
            report.total_homework = metrics.total_homework
            report.submitted_on_time = metrics.submitted_on_time
            report.submitted_late = metrics.submitted_late
            report.not_submitted = metrics.not_submitted
            report.homework_rate = metrics.homework_rate
            
            report.avg_score = metrics.avg_score
            report.score_trend = metrics.score_trend
            report.control_points_count = metrics.control_points_count
            report.control_points_avg = metrics.control_points_avg
            
            # Запускаем AI анализ
            ai_result = self._call_ai(student, group, period_start, period_end, metrics)
            
            if ai_result.error:
                report.status = 'failed'
                report.ai_analysis = {'error': ai_result.error}
            else:
                report.status = 'completed'
                report.risk_level = ai_result.risk_level
                report.reliability_score = ai_result.reliability_score
                report.ai_analysis = {
                    'profile_type': ai_result.profile_type,
                    'strengths': ai_result.strengths,
                    'concerns': ai_result.concerns,
                    'patterns': ai_result.patterns,
                    'recommendations': ai_result.recommendations,
                    'alerts': ai_result.alerts,
                    'predicted_completion_probability': ai_result.predicted_completion_probability,
                    'summary': ai_result.summary,
                }
                report.ai_confidence = ai_result.confidence
                report.ai_tokens_used = ai_result.tokens_used
                report.ai_provider = self.provider
            
            report.save()
            
        except Exception as e:
            logger.exception(f"Error generating behavior report for {student.email}")
            report.status = 'failed'
            report.ai_analysis = {'error': str(e)}
            report.save()
        
        return report

    def _call_ai(
        self,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date,
        metrics: BehaviorMetrics
    ) -> AIBehaviorResult:
        """Вызывает AI для анализа поведения"""
        
        api_url, api_key, model = self._get_api_config()
        
        if not api_key:
            return AIBehaviorResult(
                profile_type='needs_attention',
                risk_level='medium',
                reliability_score=50,
                strengths=[],
                concerns=['AI ключ не настроен'],
                patterns=[],
                recommendations=[],
                alerts=[],
                predicted_completion_probability=50,
                summary='AI анализ недоступен — не настроен API ключ',
                confidence=0,
                tokens_used=0,
                error='API key not configured'
            )
        
        # Форматируем детали занятий
        lesson_details_str = '\n'.join([
            f"  - {d['date']}: {d['title']} — {d['status']}"
            for d in metrics.lesson_details[-10:]  # Последние 10
        ]) or '  Нет данных'
        
        # Форматируем детали ДЗ
        homework_details_str = '\n'.join([
            f"  - {d['title']}: {d['status']}" + (f" (балл: {d.get('score', 'N/A')})" if d.get('score') else '')
            for d in metrics.homework_details[-10:]
        ]) or '  Нет данных'
        
        prompt = self.BEHAVIOR_ANALYSIS_PROMPT.format(
            student_name=student.get_full_name() or student.email,
            group_name=group.name if group else 'Индивидуально',
            period=f"{period_start.strftime('%d.%m.%Y')} — {period_end.strftime('%d.%m.%Y')}",
            total_lessons=metrics.total_lessons,
            attended_lessons=metrics.attended_lessons,
            attendance_rate=metrics.attendance_rate,
            missed_lessons=metrics.missed_lessons,
            late_arrivals=metrics.late_arrivals,
            total_homework=metrics.total_homework,
            submitted_on_time=metrics.submitted_on_time,
            submitted_late=metrics.submitted_late,
            not_submitted=metrics.not_submitted,
            homework_rate=metrics.homework_rate,
            avg_score=f"{metrics.avg_score:.1f}" if metrics.avg_score else 'N/A',
            score_trend=metrics.score_trend,
            control_points_count=metrics.control_points_count,
            control_points_avg=f"{metrics.control_points_avg:.1f}" if metrics.control_points_avg else 'N/A',
            lesson_details=lesson_details_str,
            homework_details=homework_details_str,
        )
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    api_url,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': 'Ты — опытный преподаватель-аналитик. Отвечай только валидным JSON.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.3,
                        'max_tokens': 2000,
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                content = data['choices'][0]['message']['content']
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                
                # Парсим JSON
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]
                
                analysis = json.loads(content.strip())
                
                return AIBehaviorResult(
                    profile_type=analysis.get('profile_type', 'needs_attention'),
                    risk_level=analysis.get('risk_level', 'medium'),
                    reliability_score=analysis.get('reliability_score', 50),
                    strengths=analysis.get('strengths', []),
                    concerns=analysis.get('concerns', []),
                    patterns=analysis.get('patterns', []),
                    recommendations=analysis.get('recommendations', []),
                    alerts=analysis.get('alerts', []),
                    predicted_completion_probability=analysis.get('predicted_completion_probability', 50),
                    summary=analysis.get('summary', ''),
                    confidence=0.8,
                    tokens_used=tokens_used,
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in behavior analysis: {e}")
            return self._fallback_analysis(metrics)
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in behavior analysis: {e}")
            return AIBehaviorResult(
                profile_type='needs_attention',
                risk_level='medium',
                reliability_score=50,
                strengths=[],
                concerns=[],
                patterns=[],
                recommendations=[],
                alerts=[],
                predicted_completion_probability=50,
                summary=f'Ошибка API: {str(e)}',
                confidence=0,
                tokens_used=0,
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Error in AI behavior analysis: {e}")
            return self._fallback_analysis(metrics)

    def _fallback_analysis(self, metrics: BehaviorMetrics) -> AIBehaviorResult:
        """Простой анализ без AI (fallback)"""
        
        # Простая эвристика
        reliability_score = 50
        risk_level = 'medium'
        profile_type = 'needs_attention'
        strengths = []
        concerns = []
        alerts = []
        
        # Посещаемость
        if metrics.attendance_rate >= 90:
            reliability_score += 25
            strengths.append('Отличная посещаемость')
        elif metrics.attendance_rate >= 70:
            reliability_score += 10
        elif metrics.attendance_rate < 50:
            reliability_score -= 20
            concerns.append(f'Низкая посещаемость ({metrics.attendance_rate:.0f}%)')
            alerts.append({'type': 'warning', 'message': 'Посещаемость ниже 50%'})
        
        # Домашние задания
        if metrics.homework_rate >= 90:
            reliability_score += 20
            strengths.append('Сдаёт все ДЗ')
        elif metrics.homework_rate < 50:
            reliability_score -= 15
            concerns.append('Не сдаёт ДЗ')
        
        if metrics.not_submitted >= 3:
            alerts.append({'type': 'warning', 'message': f'{metrics.not_submitted} несданных ДЗ'})
        
        # Определяем уровень риска
        if reliability_score >= 80:
            risk_level = 'low'
            profile_type = 'responsible'
        elif reliability_score >= 50:
            risk_level = 'medium'
            profile_type = 'needs_attention'
        else:
            risk_level = 'high'
            profile_type = 'at_risk'
        
        return AIBehaviorResult(
            profile_type=profile_type,
            risk_level=risk_level,
            reliability_score=max(0, min(100, reliability_score)),
            strengths=strengths,
            concerns=concerns,
            patterns=[],
            recommendations=[{'priority': 'medium', 'action': 'Провести личную беседу с учеником'}],
            alerts=alerts,
            predicted_completion_probability=reliability_score,
            summary=f'Оценка основана на эвристике. Посещаемость: {metrics.attendance_rate:.0f}%, Сдача ДЗ: {metrics.homework_rate:.0f}%',
            confidence=0.3,
            tokens_used=0,
        )
