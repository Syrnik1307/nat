"""
Обработчики команд студента
"""
from .lessons import (
    my_lessons,
    lesson_details,
    today_lessons,
)
from .homework import (
    my_homework,
    homework_details,
    pending_homework,
)
from .progress import (
    my_progress,
    detailed_grades,
)

__all__ = [
    # Lessons
    'my_lessons',
    'lesson_details',
    'today_lessons',
    # Homework
    'my_homework',
    'homework_details',
    'pending_homework',
    # Progress
    'my_progress',
    'detailed_grades',
]
