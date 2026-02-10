"""
Добавляет поле ai_review (JSONField) на модель Answer.
Хранит структурированный AI-ревью: criteria, strengths, weaknesses, recommendations, summary.

Nullable → безопасная миграция.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homework', '0023_add_ai_grading_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='ai_review',
            field=models.JSONField(
                null=True, blank=True,
                help_text='Структурированный AI-ревью: {criteria: [{name, score, max_score, comment}], strengths, weaknesses, recommendations, summary}',
            ),
        ),
    ]
