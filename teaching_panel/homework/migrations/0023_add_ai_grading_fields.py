"""
Добавляет поля для асинхронной AI-проверки на модель Answer.

Все поля nullable → безопасная миграция, данные не затрагиваются.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homework', '0022_homework_exam_topics'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='grading_job_id',
            field=models.UUIDField(
                null=True, blank=True, db_index=True,
                help_text='UUID задачи AI-проверки в очереди',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_grading_status',
            field=models.CharField(
                max_length=20, null=True, blank=True,
                choices=[
                    ('pending', 'В очереди'),
                    ('processing', 'Проверяется'),
                    ('completed', 'Проверено AI'),
                    ('failed', 'Ошибка AI'),
                ],
                help_text='Статус асинхронной AI-проверки',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_provider_used',
            field=models.CharField(
                max_length=30, null=True, blank=True,
                help_text='Какой AI-провайдер использован (deepseek/openai/mock)',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_cost_rubles',
            field=models.DecimalField(
                max_digits=8, decimal_places=4, null=True, blank=True,
                help_text='Стоимость AI-проверки в рублях',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_latency_ms',
            field=models.IntegerField(
                null=True, blank=True,
                help_text='Время ответа AI-провайдера в миллисекундах',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_tokens_used',
            field=models.IntegerField(
                null=True, blank=True,
                help_text='Количество токенов, использованных AI',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_checked_at',
            field=models.DateTimeField(
                null=True, blank=True,
                help_text='Время завершения AI-проверки',
            ),
        ),
        migrations.AddField(
            model_name='answer',
            name='ai_confidence',
            field=models.FloatField(
                null=True, blank=True,
                help_text='Уверенность AI (0.0 - 1.0)',
            ),
        ),
    ]
