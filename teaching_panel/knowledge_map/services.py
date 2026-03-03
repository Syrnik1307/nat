"""
Service for recalculating student topic scores.

Aggregates data from:
1. Homework answers (Question.topic FK)
2. ControlPoint results (ControlPoint.topic FK)

Weighted: homework 70% + control points 30%.
If no control points, homework alone = 100%.
"""
from django.db.models import Sum, Count, F, Q, Max
from django.db.models.functions import Coalesce
from django.db.models import Value

from .models import StudentTopicScore, Topic


def recalculate_student_topic_scores(student_id, subject_id=None):
    """
    Recalculate cached topic scores for a student.
    If subject_id given, only for that subject. Otherwise all.
    """
    from homework.models import Answer
    from analytics.models import ControlPointResult

    topic_qs = Topic.objects.all()
    if subject_id:
        topic_qs = topic_qs.filter(subject_id=subject_id)

    for topic in topic_qs:
        _recalculate_single_topic(student_id, topic)


def _recalculate_single_topic(student_id, topic):
    """Recalculate score for one student-topic pair."""
    from homework.models import Answer
    from analytics.models import ControlPointResult

    # 1. Homework answers
    hw_data = Answer.objects.filter(
        submission__student_id=student_id,
        question__topic=topic,
        submission__status__in=['submitted', 'graded'],
    ).aggregate(
        total_earned=Sum(Coalesce(F('teacher_score'), F('auto_score'), Value(0))),
        total_possible=Sum('question__points'),
        count=Count('id'),
        last_at=Max('answered_at'),
    )

    hw_earned = float(hw_data['total_earned'] or 0)
    hw_possible = float(hw_data['total_possible'] or 0)
    hw_count = hw_data['count'] or 0
    hw_last = hw_data['last_at']

    # 2. Control point results
    cp_data = ControlPointResult.objects.filter(
        student_id=student_id,
        control_point__topic=topic,
    ).aggregate(
        total_earned=Sum('points'),
        total_possible=Sum('control_point__max_points'),
        count=Count('id'),
        last_at=Max('created_at'),
    )

    cp_earned = float(cp_data['total_earned'] or 0)
    cp_possible = float(cp_data['total_possible'] or 0)
    cp_count = cp_data['count'] or 0
    cp_last = cp_data['last_at']

    total_attempts = hw_count + cp_count
    if total_attempts == 0:
        return

    # 3. Weighted average
    if hw_possible > 0 and cp_possible > 0:
        hw_pct = (hw_earned / hw_possible) * 100
        cp_pct = (cp_earned / cp_possible) * 100
        score_percent = hw_pct * 0.7 + cp_pct * 0.3
        total_earned = hw_earned + cp_earned
        total_possible = hw_possible + cp_possible
    elif hw_possible > 0:
        score_percent = (hw_earned / hw_possible) * 100
        total_earned, total_possible = hw_earned, hw_possible
    elif cp_possible > 0:
        score_percent = (cp_earned / cp_possible) * 100
        total_earned, total_possible = cp_earned, cp_possible
    else:
        return

    # 4. Trend
    trend = _calculate_trend(student_id, topic)

    # 5. Last attempt
    last_at = max(filter(None, [hw_last, cp_last]), default=None)

    # 6. Upsert
    StudentTopicScore.objects.update_or_create(
        student_id=student_id,
        topic=topic,
        defaults={
            'score_percent': round(score_percent, 1),
            'attempts_count': total_attempts,
            'total_points_earned': round(total_earned, 2),
            'total_points_possible': round(total_possible, 2),
            'trend': trend,
            'last_attempt_at': last_at,
        }
    )


def _calculate_trend(student_id, topic):
    """Compare recent 3 answers vs older 3 to determine trend."""
    from homework.models import Answer

    recent = list(
        Answer.objects.filter(
            submission__student_id=student_id,
            question__topic=topic,
            submission__status__in=['submitted', 'graded'],
        )
        .order_by('-answered_at')
        .values_list('teacher_score', 'auto_score', 'question__points')[:6]
    )

    scores = []
    for ts, auto, max_pts in recent:
        eff = ts if ts is not None else (auto or 0)
        if max_pts and max_pts > 0:
            scores.append(eff / max_pts)

    if len(scores) < 4:
        return 'stable'

    recent_avg = sum(scores[:3]) / 3
    older_avg = sum(scores[3:]) / len(scores[3:])
    diff = recent_avg - older_avg

    if diff > 0.1:
        return 'up'
    elif diff < -0.1:
        return 'down'
    return 'stable'
