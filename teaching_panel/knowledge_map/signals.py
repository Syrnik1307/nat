"""
Signals for automatic recalculation of topic scores.
All handlers check KNOWLEDGE_MAP_ENABLED before executing.
If disabled, signals are registered but no-op.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .feature_flag import KNOWLEDGE_MAP_ENABLED

logger = logging.getLogger(__name__)


@receiver(post_save, sender='homework.Answer')
def on_answer_saved(sender, instance, **kwargs):
    """Recalculate topic score when a homework answer is saved/graded."""
    if not KNOWLEDGE_MAP_ENABLED:
        return
    try:
        question = instance.question
        topic_id = getattr(question, 'topic_id', None)
        if not topic_id:
            return
        student_id = instance.submission.student_id
        subject_id = question.topic.subject_id
        transaction.on_commit(lambda sid=student_id, subj=subject_id: _safe_recalculate(sid, subj))
    except Exception:
        logger.exception("Error in on_answer_saved signal (knowledge_map)")


@receiver(post_save, sender='analytics.ControlPointResult')
def on_control_point_result_saved(sender, instance, **kwargs):
    """Recalculate topic score when a control point result is saved."""
    if not KNOWLEDGE_MAP_ENABLED:
        return
    try:
        cp = instance.control_point
        topic_id = getattr(cp, 'topic_id', None)
        if not topic_id:
            return
        student_id = instance.student_id
        subject_id = cp.topic.subject_id
        transaction.on_commit(lambda sid=student_id, subj=subject_id: _safe_recalculate(sid, subj))
    except Exception:
        logger.exception("Error in on_control_point_result_saved signal (knowledge_map)")


def _safe_recalculate(student_id, subject_id):
    """Wrapper that catches all exceptions to never break parent operations."""
    try:
        from .services import recalculate_student_topic_scores
        recalculate_student_topic_scores(student_id, subject_id)
    except Exception:
        logger.exception(
            f"Failed to recalculate knowledge_map scores "
            f"student={student_id}, subject={subject_id}"
        )
