from django.db import models
from django.conf import settings

"""Core domain models.

Duplicate educational entities (Lesson, Assignment, Submission) were moved to dedicated
apps: schedule (for lessons with Zoom pooling) and homework (for assignments & submissions).
This module now keeps only Course for high-level grouping. Migration will drop old tables.
"""


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='courses_enrolled', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'

    def __str__(self):
        return self.title
