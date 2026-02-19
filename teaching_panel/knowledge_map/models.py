"""
Knowledge Map models — карта знаний / темы экзаменов.
"""
from django.db import models


class Topic(models.Model):
    """Тема экзамена / карта знаний."""
    name = models.CharField(max_length=200, verbose_name='Название темы')
    description = models.TextField(blank=True, verbose_name='Описание')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='children',
        verbose_name='Родительская тема',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
