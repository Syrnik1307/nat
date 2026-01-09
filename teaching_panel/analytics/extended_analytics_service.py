"""
Extended Student Analytics Service

Расширенная аналитика учеников, включающая:
- Паттерны ошибок по типам вопросов
- Время выполнения и "разгон"
- Качество вопросов ученика
- Активность в чатах и социальную динамику
- Хитмап активности
"""

import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta, datetime
from collections import defaultdict

from django.conf import settings
from django.db.models import Avg, Count, Q, F, Sum, StdDev
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.utils import timezone

from accounts.models import (
    CustomUser, 
    AttendanceRecord, 
    Message, 
    StudentActivityLog,
    ChatAnalyticsSummary
)
from schedule.models import Lesson, Group
from homework.models import (
    Homework, 
    StudentSubmission, 
    Answer, 
    Question,
    AnswerVersion,
    StudentQuestion
)
from analytics.models import ControlPoint, ControlPointResult

logger = logging.getLogger(__name__)


@dataclass
class ErrorPattern:
    """Паттерн ошибок по типу вопроса"""
    question_type: str
    total_questions: int
    correct_count: int
    error_count: int
    accuracy_percent: float
    common_mistakes: List[str] = field(default_factory=list)
    error_type: str = 'unknown'  # systematic, random, careless


@dataclass
class CognitiveProfile:
    """Когнитивный профиль ученика"""
    # Предпочитаемые типы контента
    preferred_question_types: List[str] = field(default_factory=list)
    weak_question_types: List[str] = field(default_factory=list)
    
    # Время на разгон (секунды от создания submission до первого ответа)
    avg_warmup_time_seconds: Optional[float] = None
    
    # Порядок ответов (следует ли порядку вопросов)
    follows_question_order: bool = True
    order_deviation_score: float = 0.0  # 0 = строго по порядку, 1 = полный хаос
    
    # Скорость выполнения
    avg_answer_time_seconds: Optional[float] = None
    answer_time_trend: str = 'stable'  # speeding_up, slowing_down, stable
    
    # Самокоррекция
    avg_revisions_per_answer: float = 0.0
    revision_improvement_rate: float = 0.0  # Улучшается ли оценка после ревизий
    
    # Качество вопросов
    total_questions_asked: int = 0
    procedural_questions: int = 0  # "Как делать?"
    conceptual_questions: int = 0  # "Почему?"
    question_quality_score: float = 0.0  # 0-1


@dataclass
class EnergyProfile:
    """Профиль энергии/концентрации ученика"""
    # На какой минуте падает качество ответов
    fatigue_onset_minute: Optional[int] = None
    
    # Оптимальное время для занятий (часы)
    optimal_hours: List[int] = field(default_factory=list)
    
    # Дни недели с лучшей активностью
    best_days: List[int] = field(default_factory=list)  # 0=Пн, 6=Вс
    
    # Хитмап активности: {day_of_week: {hour: count}}
    activity_heatmap: Dict[int, Dict[int, int]] = field(default_factory=dict)


@dataclass
class SocialProfile:
    """Социальный профиль ученика в группе"""
    # Активность в чате
    total_messages: int = 0
    questions_asked: int = 0
    answers_given: int = 0
    helpful_messages: int = 0
    
    # Влиятельность
    times_mentioned: int = 0
    influence_score: int = 0  # 0-100
    
    # Тональность
    avg_sentiment: Optional[float] = None
    is_positive: bool = True
    
    # Роль в группе
    detected_role: str = 'observer'  # leader, helper, active, observer, silent
    
    # Сравнение с группой
    rank_in_group: Optional[int] = None
    percentile: Optional[float] = None


@dataclass
class MotivationProfile:
    """Профиль мотивации ученика"""
    # Тип мотивации
    motivation_type: str = 'unknown'  # intrinsic, extrinsic, fear_driven
    
    # Паттерн сдачи (ранняя, в дедлайн, после дедлайна)
    submission_pattern: str = 'on_time'  # early, on_time, last_minute, late
    avg_days_before_deadline: Optional[float] = None
    
    # Реакция на критику
    improves_after_feedback: bool = True
    feedback_response_score: float = 0.0  # -1 (ухудшение) до +1 (улучшение)
    
    # Стрессоустойчивость
    control_point_vs_hw_diff: Optional[float] = None  # Разница ср. балла КТ и ДЗ
    stress_resilience: str = 'normal'  # high, normal, low


@dataclass
class ExtendedStudentAnalytics:
    """Полная расширенная аналитика ученика"""
    student_id: int
    student_name: str
    group_id: Optional[int]
    group_name: Optional[str]
    period_start: date
    period_end: date
    
    # Блок 1: Академические метрики
    attendance_rate: float = 0.0
    avg_score: Optional[float] = None
    score_trend: str = 'stable'
    error_patterns: List[ErrorPattern] = field(default_factory=list)
    
    # Блок 2: Когнитивный профиль
    cognitive: CognitiveProfile = field(default_factory=CognitiveProfile)
    
    # Блок 3: Психоэмоциональный профиль
    energy: EnergyProfile = field(default_factory=EnergyProfile)
    motivation: MotivationProfile = field(default_factory=MotivationProfile)
    
    # Блок 4: Социальная динамика
    social: SocialProfile = field(default_factory=SocialProfile)
    
    # Общие рекомендации
    risk_level: str = 'low'
    key_insights: List[str] = field(default_factory=list)
    recommendations: List[Dict[str, str]] = field(default_factory=list)


class ExtendedAnalyticsService:
    """Сервис расширенной аналитики учеников"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def collect_full_analytics(
        self,
        student: CustomUser,
        group: Optional[Group] = None,
        period_days: int = 30
    ) -> ExtendedStudentAnalytics:
        """Собирает полную аналитику по ученику"""
        
        period_end = timezone.now().date()
        period_start = period_end - timedelta(days=period_days)
        
        analytics = ExtendedStudentAnalytics(
            student_id=student.id,
            student_name=student.get_full_name() or student.email,
            group_id=group.id if group else None,
            group_name=group.name if group else None,
            period_start=period_start,
            period_end=period_end,
        )
        
        # Собираем данные по блокам
        self._collect_academic_metrics(analytics, student, group, period_start, period_end)
        self._collect_error_patterns(analytics, student, group, period_start, period_end)
        self._collect_cognitive_profile(analytics, student, group, period_start, period_end)
        self._collect_energy_profile(analytics, student, group, period_start, period_end)
        self._collect_motivation_profile(analytics, student, group, period_start, period_end)
        self._collect_social_profile(analytics, student, group, period_start, period_end)
        self._generate_insights(analytics)
        
        return analytics
    
    def _collect_academic_metrics(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Собирает базовые академические метрики"""
        
        # Посещаемость
        attendance_qs = AttendanceRecord.objects.filter(
            student=student,
            lesson__start_time__date__gte=period_start,
            lesson__start_time__date__lte=period_end
        )
        if group:
            attendance_qs = attendance_qs.filter(lesson__group=group)
        
        total_lessons = attendance_qs.count()
        attended = attendance_qs.filter(status='attended').count()
        analytics.attendance_rate = (attended / total_lessons * 100) if total_lessons else 0.0
        
        # Средний балл
        submissions_qs = StudentSubmission.objects.filter(
            student=student,
            status='graded',
            graded_at__date__gte=period_start,
            graded_at__date__lte=period_end
        )
        if group:
            submissions_qs = submissions_qs.filter(homework__lesson__group=group)
        
        avg_result = submissions_qs.aggregate(avg=Avg('total_score'))
        analytics.avg_score = avg_result['avg']
        
        # Тренд оценок
        if submissions_qs.count() >= 4:
            recent = list(submissions_qs.order_by('-graded_at')[:2].values_list('total_score', flat=True))
            older = list(submissions_qs.order_by('-graded_at')[2:4].values_list('total_score', flat=True))
            
            if recent and older:
                recent_avg = sum(recent) / len(recent) if recent else 0
                older_avg = sum(older) / len(older) if older else 0
                
                if recent_avg > older_avg * 1.1:
                    analytics.score_trend = 'improving'
                elif recent_avg < older_avg * 0.9:
                    analytics.score_trend = 'declining'
                else:
                    analytics.score_trend = 'stable'
    
    def _collect_error_patterns(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Анализирует паттерны ошибок по типам вопросов"""
        
        answers_qs = Answer.objects.filter(
            submission__student=student,
            submission__created_at__date__gte=period_start,
            submission__created_at__date__lte=period_end
        ).select_related('question')
        
        if group:
            answers_qs = answers_qs.filter(submission__homework__lesson__group=group)
        
        # Группируем по типу вопроса
        type_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'errors': 0})
        
        for answer in answers_qs:
            q_type = answer.question.question_type
            max_score = answer.question.points
            actual_score = answer.teacher_score if answer.teacher_score is not None else answer.auto_score
            
            type_stats[q_type]['total'] += 1
            if actual_score is not None:
                if actual_score >= max_score * 0.8:
                    type_stats[q_type]['correct'] += 1
                else:
                    type_stats[q_type]['errors'] += 1
        
        # Создаём паттерны ошибок
        for q_type, stats in type_stats.items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total'] * 100
                
                # Определяем тип ошибки
                error_type = 'random'
                if accuracy < 50:
                    error_type = 'systematic'  # Системные ошибки
                elif stats['errors'] > 0 and accuracy > 80:
                    error_type = 'careless'  # Невнимательность
                
                pattern = ErrorPattern(
                    question_type=q_type,
                    total_questions=stats['total'],
                    correct_count=stats['correct'],
                    error_count=stats['errors'],
                    accuracy_percent=accuracy,
                    error_type=error_type
                )
                analytics.error_patterns.append(pattern)
        
        # Сортируем по количеству ошибок
        analytics.error_patterns.sort(key=lambda x: x.error_count, reverse=True)
    
    def _collect_cognitive_profile(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Собирает когнитивный профиль"""
        
        cognitive = analytics.cognitive
        
        # Предпочитаемые/слабые типы вопросов (из error_patterns)
        for pattern in analytics.error_patterns:
            if pattern.accuracy_percent >= 80:
                cognitive.preferred_question_types.append(pattern.question_type)
            elif pattern.accuracy_percent < 50:
                cognitive.weak_question_types.append(pattern.question_type)
        
        # Время на разгон
        submissions_qs = StudentSubmission.objects.filter(
            student=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).prefetch_related('answers')
        
        if group:
            submissions_qs = submissions_qs.filter(homework__lesson__group=group)
        
        warmup_times = []
        order_deviations = []
        answer_times = []
        
        for submission in submissions_qs:
            answers = list(submission.answers.order_by('answered_at').all())
            
            if answers and answers[0].answered_at:
                # Время от создания submission до первого ответа
                first_answer = answers[0]
                if first_answer.started_at:
                    warmup_delta = (first_answer.started_at - submission.created_at).total_seconds()
                    if warmup_delta > 0:
                        warmup_times.append(warmup_delta)
            
            # Порядок ответов vs порядок вопросов
            if len(answers) >= 3:
                expected_order = [a.question.order for a in sorted(answers, key=lambda x: x.question.order)]
                actual_order = [a.question.order for a in answers if a.answered_at]
                
                if actual_order:
                    # Считаем количество инверсий
                    inversions = 0
                    for i in range(len(actual_order)):
                        for j in range(i + 1, len(actual_order)):
                            if actual_order[i] > actual_order[j]:
                                inversions += 1
                    max_inversions = len(actual_order) * (len(actual_order) - 1) / 2
                    deviation = inversions / max_inversions if max_inversions > 0 else 0
                    order_deviations.append(deviation)
            
            # Время на ответ
            for answer in answers:
                if answer.time_spent_seconds:
                    answer_times.append(answer.time_spent_seconds)
        
        if warmup_times:
            cognitive.avg_warmup_time_seconds = sum(warmup_times) / len(warmup_times)
        
        if order_deviations:
            cognitive.order_deviation_score = sum(order_deviations) / len(order_deviations)
            cognitive.follows_question_order = cognitive.order_deviation_score < 0.3
        
        if answer_times:
            cognitive.avg_answer_time_seconds = sum(answer_times) / len(answer_times)
        
        # Самокоррекция (ревизии)
        revisions_qs = Answer.objects.filter(
            submission__student=student,
            submission__created_at__date__gte=period_start,
            submission__created_at__date__lte=period_end,
            revision_count__gt=0
        ).aggregate(avg_rev=Avg('revision_count'))
        
        if revisions_qs['avg_rev']:
            cognitive.avg_revisions_per_answer = revisions_qs['avg_rev']
        
        # Качество вопросов ученика
        student_questions = StudentQuestion.objects.filter(
            student=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        if group:
            student_questions = student_questions.filter(group=group)
        
        cognitive.total_questions_asked = student_questions.count()
        cognitive.procedural_questions = student_questions.filter(quality='procedural').count()
        cognitive.conceptual_questions = student_questions.filter(quality='conceptual').count()
        
        if cognitive.total_questions_asked > 0:
            # Концептуальные вопросы считаются более качественными
            cognitive.question_quality_score = (
                (cognitive.conceptual_questions * 2 + cognitive.procedural_questions) /
                (cognitive.total_questions_asked * 2)
            )
    
    def _collect_energy_profile(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Собирает профиль энергии/концентрации"""
        
        energy = analytics.energy
        
        # Хитмап активности
        activity_logs = StudentActivityLog.objects.filter(
            student=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        if group:
            activity_logs = activity_logs.filter(group=group)
        
        heatmap = defaultdict(lambda: defaultdict(int))
        for log in activity_logs:
            heatmap[log.day_of_week][log.hour_of_day] += 1
        
        energy.activity_heatmap = {day: dict(hours) for day, hours in heatmap.items()}
        
        # Оптимальные часы (топ-3 по активности)
        hour_totals = defaultdict(int)
        day_totals = defaultdict(int)
        
        for day, hours in heatmap.items():
            for hour, count in hours.items():
                hour_totals[hour] += count
                day_totals[day] += count
        
        if hour_totals:
            sorted_hours = sorted(hour_totals.items(), key=lambda x: x[1], reverse=True)
            energy.optimal_hours = [h for h, _ in sorted_hours[:3]]
        
        if day_totals:
            sorted_days = sorted(day_totals.items(), key=lambda x: x[1], reverse=True)
            energy.best_days = [d for d, _ in sorted_days[:2]]
        
        # Анализ падения качества в течение сессии
        # Ищем сессии ДЗ где есть время на ответы
        sessions = StudentSubmission.objects.filter(
            student=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).prefetch_related('answers')
        
        if group:
            sessions = sessions.filter(homework__lesson__group=group)
        
        fatigue_points = []
        for submission in sessions:
            answers = list(submission.answers.order_by('answered_at').all())
            if len(answers) >= 5:
                # Сравниваем качество первой и последней трети
                third = len(answers) // 3
                first_scores = []
                last_scores = []
                
                for i, ans in enumerate(answers):
                    score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
                    max_score = ans.question.points
                    if score is not None and max_score > 0:
                        normalized = score / max_score
                        if i < third:
                            first_scores.append(normalized)
                        elif i >= len(answers) - third:
                            last_scores.append(normalized)
                
                if first_scores and last_scores:
                    first_avg = sum(first_scores) / len(first_scores)
                    last_avg = sum(last_scores) / len(last_scores)
                    
                    if last_avg < first_avg * 0.8:  # Падение качества более 20%
                        # Примерно оцениваем минуту падения
                        if answers[0].started_at and answers[-1].answered_at:
                            session_minutes = (answers[-1].answered_at - answers[0].started_at).total_seconds() / 60
                            fatigue_minute = int(session_minutes * 0.7)  # Примерно 70% сессии
                            fatigue_points.append(fatigue_minute)
        
        if fatigue_points:
            energy.fatigue_onset_minute = int(sum(fatigue_points) / len(fatigue_points))
    
    def _collect_motivation_profile(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Собирает профиль мотивации"""
        
        motivation = analytics.motivation
        
        # Паттерн сдачи относительно дедлайна
        submissions_with_deadline = StudentSubmission.objects.filter(
            student=student,
            homework__deadline__isnull=False,
            submitted_at__isnull=False,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).select_related('homework')
        
        if group:
            submissions_with_deadline = submissions_with_deadline.filter(homework__lesson__group=group)
        
        days_before_deadlines = []
        late_count = 0
        last_minute_count = 0
        early_count = 0
        
        for sub in submissions_with_deadline:
            if sub.submitted_at and sub.homework.deadline:
                delta = (sub.homework.deadline - sub.submitted_at).total_seconds() / 86400  # В днях
                days_before_deadlines.append(delta)
                
                if delta < 0:
                    late_count += 1
                elif delta < 0.5:  # Менее 12 часов до дедлайна
                    last_minute_count += 1
                elif delta > 2:  # Более 2 дней до дедлайна
                    early_count += 1
        
        if days_before_deadlines:
            motivation.avg_days_before_deadline = sum(days_before_deadlines) / len(days_before_deadlines)
            
            total = len(days_before_deadlines)
            if late_count / total > 0.3:
                motivation.submission_pattern = 'late'
            elif last_minute_count / total > 0.5:
                motivation.submission_pattern = 'last_minute'
            elif early_count / total > 0.3:
                motivation.submission_pattern = 'early'
            else:
                motivation.submission_pattern = 'on_time'
        
        # Определяем тип мотивации
        if motivation.submission_pattern == 'early' and analytics.attendance_rate > 90:
            motivation.motivation_type = 'intrinsic'
        elif motivation.submission_pattern in ['late', 'last_minute']:
            motivation.motivation_type = 'fear_driven'
        else:
            motivation.motivation_type = 'extrinsic'
        
        # Стрессоустойчивость: сравнение КТ и обычных ДЗ
        hw_avg = StudentSubmission.objects.filter(
            student=student,
            status='graded',
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).aggregate(avg=Avg('total_score'))['avg']
        
        cp_avg = ControlPointResult.objects.filter(
            student=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        ).aggregate(avg=Avg('points'))['avg']
        
        if hw_avg and cp_avg:
            motivation.control_point_vs_hw_diff = cp_avg - hw_avg
            if motivation.control_point_vs_hw_diff < -10:
                motivation.stress_resilience = 'low'
            elif motivation.control_point_vs_hw_diff > 5:
                motivation.stress_resilience = 'high'
            else:
                motivation.stress_resilience = 'normal'
    
    def _collect_social_profile(
        self,
        analytics: ExtendedStudentAnalytics,
        student: CustomUser,
        group: Optional[Group],
        period_start: date,
        period_end: date
    ):
        """Собирает социальный профиль"""
        
        social = analytics.social
        
        if not group:
            return
        
        # Пытаемся найти готовую аналитику чата
        chat_summary = ChatAnalyticsSummary.objects.filter(
            student=student,
            group=group,
            period_start__lte=period_start,
            period_end__gte=period_end
        ).first()
        
        if chat_summary:
            social.total_messages = chat_summary.total_messages
            social.questions_asked = chat_summary.questions_asked
            social.answers_given = chat_summary.answers_given
            social.helpful_messages = chat_summary.helpful_messages
            social.times_mentioned = chat_summary.times_mentioned
            social.influence_score = chat_summary.influence_score
            social.avg_sentiment = chat_summary.avg_sentiment
            social.detected_role = chat_summary.detected_role
            social.is_positive = (chat_summary.avg_sentiment or 0) >= 0
        else:
            # Считаем напрямую из сообщений
            group_chats = group.chats.all()
            
            messages = Message.objects.filter(
                chat__in=group_chats,
                sender=student,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end
            )
            
            social.total_messages = messages.count()
            social.questions_asked = messages.filter(message_type='question').count()
            social.answers_given = messages.filter(message_type='answer').count()
            social.helpful_messages = messages.filter(is_helpful=True).count()
            
            # Упоминания
            social.times_mentioned = Message.objects.filter(
                chat__in=group_chats,
                mentioned_users=student,
                created_at__date__gte=period_start,
                created_at__date__lte=period_end
            ).count()
            
            # Сентимент
            sentiment_result = messages.aggregate(avg=Avg('sentiment_score'))
            social.avg_sentiment = sentiment_result['avg']
            social.is_positive = (social.avg_sentiment or 0) >= 0
            
            # Вычисляем influence score
            social.influence_score = min(100, (
                social.times_mentioned * 3 +
                social.answers_given * 2 +
                social.helpful_messages * 2 +
                int(social.total_messages * 0.1)
            ))
            
            # Определяем роль
            if social.influence_score >= 50 and social.total_messages >= 20:
                social.detected_role = 'leader'
            elif social.helpful_messages >= 5 or social.answers_given >= 10:
                social.detected_role = 'helper'
            elif social.total_messages >= 10:
                social.detected_role = 'active'
            elif social.total_messages >= 3:
                social.detected_role = 'observer'
            else:
                social.detected_role = 'silent'
        
        # Ранг в группе
        from accounts.models import UserRating
        
        student_rating = UserRating.objects.filter(user=student, group=group).first()
        if student_rating:
            higher_count = UserRating.objects.filter(
                group=group,
                total_points__gt=student_rating.total_points
            ).count()
            social.rank_in_group = higher_count + 1
            
            total_in_group = UserRating.objects.filter(group=group).count()
            if total_in_group > 0:
                social.percentile = (1 - higher_count / total_in_group) * 100
    
    def _generate_insights(self, analytics: ExtendedStudentAnalytics):
        """Генерирует ключевые инсайты и рекомендации"""
        
        insights = []
        recommendations = []
        
        # Анализ посещаемости
        if analytics.attendance_rate < 70:
            insights.append(f"⚠️ Низкая посещаемость: {analytics.attendance_rate:.0f}%")
            recommendations.append({
                'priority': 'high',
                'action': 'Связаться с учеником для выяснения причин пропусков'
            })
        
        # Анализ ошибок
        for pattern in analytics.error_patterns[:2]:
            if pattern.error_type == 'systematic' and pattern.error_count >= 3:
                insights.append(f"📉 Системные ошибки в типе '{pattern.question_type}': {pattern.accuracy_percent:.0f}% точность")
                recommendations.append({
                    'priority': 'high',
                    'action': f'Провести дополнительную работу над типом вопросов "{pattern.question_type}"'
                })
        
        # Когнитивный профиль
        if analytics.cognitive.avg_warmup_time_seconds and analytics.cognitive.avg_warmup_time_seconds > 600:
            insights.append(f"🐢 Долгий разгон: ~{analytics.cognitive.avg_warmup_time_seconds/60:.0f} мин до начала работы")
        
        if not analytics.cognitive.follows_question_order:
            insights.append("🔀 Ученик предпочитает хаотичный порядок вопросов")
        
        if analytics.cognitive.question_quality_score > 0.7:
            insights.append("💡 Задаёт качественные концептуальные вопросы")
        
        # Энергия
        if analytics.energy.fatigue_onset_minute and analytics.energy.fatigue_onset_minute < 30:
            insights.append(f"⚡ Концентрация падает на ~{analytics.energy.fatigue_onset_minute} минуте")
            recommendations.append({
                'priority': 'medium',
                'action': 'Рассмотреть более короткие блоки заданий или перерывы'
            })
        
        if analytics.energy.optimal_hours:
            hours_str = ', '.join([f"{h}:00" for h in analytics.energy.optimal_hours])
            insights.append(f"🕐 Оптимальное время для занятий: {hours_str}")
        
        # Мотивация
        if analytics.motivation.motivation_type == 'fear_driven':
            insights.append("😰 Мотивация 'от страха' — сдаёт в последний момент")
            recommendations.append({
                'priority': 'medium',
                'action': 'Попробовать систему промежуточных дедлайнов'
            })
        
        if analytics.motivation.stress_resilience == 'low':
            insights.append("📊 Оценки падают на контрольных (стресс)")
            recommendations.append({
                'priority': 'medium',
                'action': 'Провести подготовительную работу перед контрольными'
            })
        
        # Социальная динамика
        if analytics.social.detected_role == 'leader':
            insights.append("👑 Неформальный лидер группы")
        elif analytics.social.detected_role == 'helper':
            insights.append("🤝 Активно помогает другим ученикам")
        elif analytics.social.detected_role == 'silent':
            insights.append("🔇 Низкая активность в группе")
            recommendations.append({
                'priority': 'low',
                'action': 'Попробовать вовлечь в групповую работу'
            })
        
        if analytics.social.is_positive == False and analytics.social.total_messages > 5:
            insights.append("😤 Преобладает негативная тональность в чате")
            recommendations.append({
                'priority': 'medium',
                'action': 'Обратить внимание на эмоциональное состояние ученика'
            })
        
        # Определяем общий уровень риска
        risk_factors = 0
        if analytics.attendance_rate < 60:
            risk_factors += 2
        elif analytics.attendance_rate < 80:
            risk_factors += 1
        
        if analytics.score_trend == 'declining':
            risk_factors += 2
        
        if analytics.motivation.submission_pattern == 'late':
            risk_factors += 1
        
        if analytics.social.detected_role == 'silent':
            risk_factors += 1
        
        if risk_factors >= 4:
            analytics.risk_level = 'high'
        elif risk_factors >= 2:
            analytics.risk_level = 'medium'
        else:
            analytics.risk_level = 'low'
        
        analytics.key_insights = insights
        analytics.recommendations = recommendations


def log_student_activity(
    student: CustomUser,
    action_type: str,
    group: Optional[Group] = None,
    details: Optional[Dict] = None
):
    """Хелпер для логирования активности ученика"""
    try:
        StudentActivityLog.objects.create(
            student=student,
            action_type=action_type,
            group=group,
            details=details or {}
        )
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")


def recalculate_chat_analytics(group: Group, period_days: int = 30):
    """Пересчитывает агрегированную аналитику чатов для группы"""
    
    period_end = timezone.now().date()
    period_start = period_end - timedelta(days=period_days)
    
    # Получаем всех студентов группы
    from schedule.models import StudentGroupMembership
    students = CustomUser.objects.filter(
        group_memberships__group=group,
        role='student'
    ).distinct()
    
    group_chats = group.chats.all()
    
    for student in students:
        messages = Message.objects.filter(
            chat__in=group_chats,
            sender=student,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end
        )
        
        summary, created = ChatAnalyticsSummary.objects.update_or_create(
            student=student,
            group=group,
            period_start=period_start,
            period_end=period_end,
            defaults={
                'total_messages': messages.count(),
                'questions_asked': messages.filter(message_type='question').count(),
                'answers_given': messages.filter(message_type='answer').count(),
                'helpful_messages': messages.filter(is_helpful=True).count(),
                'times_mentioned': Message.objects.filter(
                    chat__in=group_chats,
                    mentioned_users=student,
                    created_at__date__gte=period_start
                ).count(),
                'times_mentioning_others': messages.filter(
                    mentioned_users__isnull=False
                ).distinct().count(),
                'positive_messages': messages.filter(sentiment_score__gt=0.3).count(),
                'negative_messages': messages.filter(sentiment_score__lt=-0.3).count(),
                'neutral_messages': messages.filter(
                    sentiment_score__gte=-0.3,
                    sentiment_score__lte=0.3
                ).count(),
            }
        )
        
        # Вычисляем средний сентимент
        sentiment = messages.aggregate(avg=Avg('sentiment_score'))
        summary.avg_sentiment = sentiment['avg']
        
        # Вычисляем influence score и роль
        summary.compute_influence_score()
        summary.detect_role()
        summary.save()
