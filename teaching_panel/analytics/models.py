from django.db import models
from django.conf import settings
from schedule.models import Lesson, Group

class ControlPoint(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='control_points', limit_choices_to={'role': 'teacher'})
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='control_points')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='control_points')
    title = models.CharField(max_length=255)
    max_points = models.IntegerField(default=100)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'контрольная точка'
        verbose_name_plural = 'контрольные точки'

    def __str__(self):
        return f"{self.title} ({self.group.name})"

class ControlPointResult(models.Model):
    control_point = models.ForeignKey(ControlPoint, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='control_point_results', limit_choices_to={'role': 'student'})
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['control_point', 'student']
        verbose_name = 'результат контрольной точки'
        verbose_name_plural = 'результаты контрольных точек'

    def __str__(self):
        return f"{self.student.email} -> {self.control_point.title}: {self.points}"
