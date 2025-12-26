"""
AI Student Analytics Service - анализ ошибок и прогресса студентов

Генерирует персональные отчёты для преподавателей на основе:
- Ответов студента на ДЗ
- Оценок AI и комментариев
- Паттернов ошибок
"""

import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class StudentAnalysisData:
    """Данные для анализа студента"""
    student_name: str
    student_email: str
    total_submissions: int
    avg_score_percent: float
    total_questions: int
    text_answers: List[Dict[str, Any]]  # Текстовые ответы с фидбеком
    question_types_stats: Dict[str, Dict[str, int]]  # Статистика по типам вопросов
    recent_trend: str  # improving, stable, declining


@dataclass
class AIAnalysisResult:
    """Результат AI анализа"""
    strengths: List[str]
    weaknesses: List[str]
    common_mistakes: List[Dict[str, Any]]
    recommendations: List[str]
    progress_trend: str
    summary: str
    confidence: float
    tokens_used: int
    error: Optional[str] = None


class StudentAnalyticsService:
    """Сервис AI-аналитики студентов"""
    
    ANALYSIS_PROMPT = """Ты — опытный преподаватель-аналитик. Проанализируй успеваемость студента.

ДАННЫЕ СТУДЕНТА:
{student_data}

ЗАДАЧА:
1. Определи сильные стороны студента (что получается хорошо)
2. Определи слабые стороны (где нужна работа)
3. Выяви типичные ошибки и паттерны
4. Дай конкретные рекомендации для улучшения
5. Оцени тренд прогресса

ВАЖНО:
- Будь конкретным и конструктивным
- Давай практические рекомендации
- Учитывай контекст (какие темы изучаются)
- Пиши на русском языке

Ответь СТРОГО в формате JSON:
{{
    "strengths": ["Сильная сторона 1", "Сильная сторона 2"],
    "weaknesses": ["Слабая сторона 1", "Слабая сторона 2"],
    "common_mistakes": [
        {{"topic": "Тема ошибки", "frequency": 3, "description": "Описание типичной ошибки"}}
    ],
    "recommendations": ["Конкретная рекомендация 1", "Конкретная рекомендация 2"],
    "progress_trend": "improving|stable|declining",
    "summary": "2-3 предложения с общим выводом о студенте и его прогрессе"
}}"""

    def __init__(self, provider: str = 'deepseek'):
        self.provider = provider
        self.timeout = 60  # Больше таймаут для аналитики
        
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
            raise ValueError(f"Неизвестный провайдер: {self.provider}")
    
    def collect_student_data(
        self, 
        student, 
        teacher,
        group=None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> StudentAnalysisData:
        """Собирает данные студента для анализа"""
        from homework.models import StudentSubmission, Answer
        
        # Фильтр по периоду
        if not period_start:
            period_start = date.today() - timedelta(days=30)
        if not period_end:
            period_end = date.today()
        
        # Базовый queryset submissions
        submissions_qs = StudentSubmission.objects.filter(
            student=student,
            homework__teacher=teacher,
            created_at__date__gte=period_start,
            created_at__date__lte=period_end,
            status__in=['submitted', 'graded']
        ).select_related('homework')
        
        if group:
            submissions_qs = submissions_qs.filter(homework__lesson__group=group)
        
        submissions = list(submissions_qs)
        total_submissions = len(submissions)
        
        # Средний балл
        scores = [s.total_score for s in submissions if s.total_score is not None]
        max_scores = []
        for s in submissions:
            max_score = sum(q.points for q in s.homework.questions.all())
            if max_score > 0:
                max_scores.append((s.total_score or 0, max_score))
        
        if max_scores:
            avg_score_percent = sum(s/m*100 for s, m in max_scores) / len(max_scores)
        else:
            avg_score_percent = 0.0
        
        # Собираем текстовые ответы с фидбеком
        submission_ids = [s.id for s in submissions]
        answers = Answer.objects.filter(
            submission_id__in=submission_ids,
            question__question_type='TEXT'
        ).select_related('question', 'submission__homework')
        
        text_answers = []
        for ans in answers:
            if ans.text_answer:
                text_answers.append({
                    'homework_title': ans.submission.homework.title,
                    'question': ans.question.prompt[:200],
                    'answer': ans.text_answer[:500],
                    'score': ans.teacher_score if ans.teacher_score is not None else ans.auto_score,
                    'max_score': ans.question.points,
                    'feedback': ans.teacher_feedback[:300] if ans.teacher_feedback else None
                })
        
        # Статистика по типам вопросов
        all_answers = Answer.objects.filter(submission_id__in=submission_ids).select_related('question')
        question_types_stats = {}
        for ans in all_answers:
            qtype = ans.question.question_type
            if qtype not in question_types_stats:
                question_types_stats[qtype] = {'total': 0, 'correct': 0, 'partial': 0, 'wrong': 0}
            
            question_types_stats[qtype]['total'] += 1
            score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
            max_score = ans.question.points
            
            if score is not None and max_score > 0:
                ratio = score / max_score
                if ratio >= 0.9:
                    question_types_stats[qtype]['correct'] += 1
                elif ratio >= 0.5:
                    question_types_stats[qtype]['partial'] += 1
                else:
                    question_types_stats[qtype]['wrong'] += 1
        
        # Определяем тренд (сравниваем первую и вторую половину периода)
        mid_date = period_start + (period_end - period_start) / 2
        first_half = [s for s in submissions if s.created_at.date() < mid_date]
        second_half = [s for s in submissions if s.created_at.date() >= mid_date]
        
        def avg_percent(subs):
            if not subs:
                return None
            scores = []
            for s in subs:
                max_score = sum(q.points for q in s.homework.questions.all())
                if max_score > 0 and s.total_score is not None:
                    scores.append(s.total_score / max_score * 100)
            return sum(scores) / len(scores) if scores else None
        
        first_avg = avg_percent(first_half)
        second_avg = avg_percent(second_half)
        
        if first_avg is None or second_avg is None:
            recent_trend = 'stable'
        elif second_avg > first_avg + 5:
            recent_trend = 'improving'
        elif second_avg < first_avg - 5:
            recent_trend = 'declining'
        else:
            recent_trend = 'stable'
        
        return StudentAnalysisData(
            student_name=student.get_full_name() or student.email,
            student_email=student.email,
            total_submissions=total_submissions,
            avg_score_percent=round(avg_score_percent, 1),
            total_questions=all_answers.count(),
            text_answers=text_answers[-10:],  # Последние 10
            question_types_stats=question_types_stats,
            recent_trend=recent_trend
        )
    
    def generate_analysis(self, data: StudentAnalysisData) -> AIAnalysisResult:
        """Генерирует AI анализ на основе данных студента"""
        import httpx
        
        api_url, api_key, model = self._get_api_config()
        
        if not api_key:
            return AIAnalysisResult(
                strengths=[],
                weaknesses=[],
                common_mistakes=[],
                recommendations=["Настройте API ключ для AI анализа"],
                progress_trend='stable',
                summary="AI анализ недоступен: не настроен API ключ",
                confidence=0.0,
                tokens_used=0,
                error=f"Missing API key for {self.provider}"
            )
        
        # Формируем данные для промпта
        student_data_text = f"""
Студент: {data.student_name}
Email: {data.student_email}
Всего сдано ДЗ: {data.total_submissions}
Средний балл: {data.avg_score_percent}%
Всего ответов: {data.total_questions}
Тренд прогресса: {data.recent_trend}

СТАТИСТИКА ПО ТИПАМ ВОПРОСОВ:
{json.dumps(data.question_types_stats, ensure_ascii=False, indent=2)}

ПОСЛЕДНИЕ ТЕКСТОВЫЕ ОТВЕТЫ С ОЦЕНКАМИ:
"""
        for ans in data.text_answers:
            student_data_text += f"""
---
ДЗ: {ans['homework_title']}
Вопрос: {ans['question']}
Ответ студента: {ans['answer']}
Оценка: {ans['score']}/{ans['max_score']}
Комментарий: {ans['feedback'] or 'Нет'}
"""
        
        prompt = self.ANALYSIS_PROMPT.format(student_data=student_data_text)
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.4,
                        "max_tokens": 1500
                    }
                )
                
                response.raise_for_status()
                resp_data = response.json()
                
                ai_text = resp_data['choices'][0]['message']['content'].strip()
                tokens_used = resp_data.get('usage', {}).get('total_tokens', 0)
                
                return self._parse_analysis_response(ai_text, tokens_used)
                
        except httpx.TimeoutException:
            logger.warning(f"AI analytics timeout for provider {self.provider}")
            return AIAnalysisResult(
                strengths=[],
                weaknesses=[],
                common_mistakes=[],
                recommendations=["Повторите запрос позже"],
                progress_trend=data.recent_trend,
                summary="AI анализ: таймаут запроса",
                confidence=0.0,
                tokens_used=0,
                error="Timeout"
            )
        except Exception as e:
            logger.exception(f"AI analytics error: {e}")
            return AIAnalysisResult(
                strengths=[],
                weaknesses=[],
                common_mistakes=[],
                recommendations=[],
                progress_trend=data.recent_trend,
                summary=f"Ошибка AI анализа: {str(e)[:100]}",
                confidence=0.0,
                tokens_used=0,
                error=str(e)
            )
    
    def _parse_analysis_response(self, ai_text: str, tokens_used: int) -> AIAnalysisResult:
        """Парсит JSON ответ от AI"""
        try:
            # Убираем markdown обёртку если есть
            if '```json' in ai_text:
                ai_text = ai_text.split('```json')[1].split('```')[0]
            elif '```' in ai_text:
                ai_text = ai_text.split('```')[1].split('```')[0]
            
            data = json.loads(ai_text.strip())
            
            return AIAnalysisResult(
                strengths=data.get('strengths', [])[:5],
                weaknesses=data.get('weaknesses', [])[:5],
                common_mistakes=data.get('common_mistakes', [])[:5],
                recommendations=data.get('recommendations', [])[:5],
                progress_trend=data.get('progress_trend', 'stable'),
                summary=data.get('summary', 'Анализ завершён'),
                confidence=0.85,
                tokens_used=tokens_used
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI analytics response: {ai_text[:200]}...")
            return AIAnalysisResult(
                strengths=[],
                weaknesses=[],
                common_mistakes=[],
                recommendations=[],
                progress_trend='stable',
                summary=f"Не удалось распознать ответ AI",
                confidence=0.0,
                tokens_used=tokens_used,
                error="Parse error"
            )


def generate_student_report(
    student,
    teacher,
    group=None,
    period_days: int = 30,
    provider: str = 'deepseek'
) -> 'StudentAIReport':
    """
    Генерирует AI-отчёт по студенту.
    
    Returns:
        StudentAIReport instance (saved to DB)
    """
    from .models import StudentAIReport
    
    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)
    
    # Проверяем, есть ли уже отчёт за этот период
    existing = StudentAIReport.objects.filter(
        student=student,
        teacher=teacher,
        period_start=period_start,
        period_end=period_end
    ).first()
    
    if existing and existing.status == 'completed':
        return existing
    
    # Создаём или обновляем отчёт
    report, created = StudentAIReport.objects.update_or_create(
        student=student,
        teacher=teacher,
        period_start=period_start,
        period_end=period_end,
        defaults={
            'group': group,
            'status': 'generating',
            'ai_provider': provider
        }
    )
    
    try:
        service = StudentAnalyticsService(provider=provider)
        
        # Собираем данные
        student_data = service.collect_student_data(
            student=student,
            teacher=teacher,
            group=group,
            period_start=period_start,
            period_end=period_end
        )
        
        # Обновляем статистику
        report.total_submissions = student_data.total_submissions
        report.avg_score_percent = student_data.avg_score_percent
        report.total_questions_answered = student_data.total_questions
        
        # Генерируем AI анализ
        analysis = service.generate_analysis(student_data)
        
        if analysis.error:
            report.status = 'failed'
            report.ai_analysis = {'error': analysis.error}
        else:
            report.status = 'completed'
            report.ai_analysis = {
                'strengths': analysis.strengths,
                'weaknesses': analysis.weaknesses,
                'common_mistakes': analysis.common_mistakes,
                'recommendations': analysis.recommendations,
                'progress_trend': analysis.progress_trend,
                'summary': analysis.summary
            }
            report.ai_confidence = analysis.confidence
            report.ai_tokens_used = analysis.tokens_used
        
        report.save()
        return report
        
    except Exception as e:
        logger.exception(f"Failed to generate student report: {e}")
        report.status = 'failed'
        report.ai_analysis = {'error': str(e)}
        report.save()
        return report
