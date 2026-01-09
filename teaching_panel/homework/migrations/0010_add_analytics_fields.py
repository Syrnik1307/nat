# Generated migration for student analytics fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('schedule', '0013_add_telegram_fields'),
        ('homework', '0009_add_deadline_field'),
    ]

    operations = [
        # Новые поля для Answer
        migrations.AddField(
            model_name='answer',
            name='answered_at',
            field=models.DateTimeField(blank=True, help_text='Время ответа на вопрос (для анализа порядка и скорости)', null=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='time_spent_seconds',
            field=models.IntegerField(blank=True, help_text='Время в секундах, затраченное на ответ', null=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='started_at',
            field=models.DateTimeField(blank=True, help_text='Когда ученик начал отвечать на вопрос', null=True),
        ),
        migrations.AddField(
            model_name='answer',
            name='revision_count',
            field=models.IntegerField(default=0, help_text='Сколько раз ученик изменял ответ (самокоррекция)'),
        ),
        # Индекс для Answer
        migrations.AddIndex(
            model_name='answer',
            index=models.Index(fields=['submission', 'answered_at'], name='answer_timing_idx'),
        ),
        
        # Модель AnswerVersion
        migrations.CreateModel(
            name='AnswerVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version_number', models.PositiveIntegerField(default=1, help_text='Номер версии (1 = первый ответ)')),
                ('text_content', models.TextField(blank=True, help_text='Текст ответа на момент этой версии')),
                ('selected_choice_ids', models.JSONField(blank=True, default=list, help_text='ID выбранных вариантов на момент этой версии')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='homework.answer', verbose_name='ответ')),
            ],
            options={
                'verbose_name': 'версия ответа',
                'verbose_name_plural': 'версии ответов',
                'ordering': ['answer', 'version_number'],
                'unique_together': {('answer', 'version_number')},
            },
        ),
        migrations.AddIndex(
            model_name='answerversion',
            index=models.Index(fields=['answer', '-created_at'], name='answer_version_idx'),
        ),
        
        # Модель StudentQuestion
        migrations.CreateModel(
            name='StudentQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question_text', models.TextField(verbose_name='текст вопроса')),
                ('source', models.CharField(choices=[('chat', 'Чат группы'), ('lesson', 'На уроке'), ('homework', 'В домашнем задании'), ('direct', 'Личное сообщение')], default='chat', max_length=20, verbose_name='источник')),
                ('quality', models.CharField(choices=[('procedural', 'Процедурный (как?)'), ('conceptual', 'Концептуальный (почему?)'), ('clarification', 'Уточнение'), ('off_topic', 'Не по теме'), ('unclassified', 'Не классифицирован')], default='unclassified', max_length=20, verbose_name='качество вопроса')),
                ('ai_quality_score', models.FloatField(blank=True, help_text='AI оценка качества вопроса 0-1', null=True)),
                ('ai_classification', models.JSONField(blank=True, default=dict, help_text='AI классификация: {"type": "...", "confidence": 0.9, "topics": [...]}')),
                ('is_answered', models.BooleanField(default=False)),
                ('answer_text', models.TextField(blank=True)),
                ('answered_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='asked_questions', to=settings.AUTH_USER_MODEL, verbose_name='ученик')),
                ('teacher', models.ForeignKey(limit_choices_to={'role': 'teacher'}, on_delete=django.db.models.deletion.CASCADE, related_name='received_questions', to=settings.AUTH_USER_MODEL, verbose_name='учитель')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_questions', to='schedule.group', verbose_name='группа')),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_questions', to='schedule.lesson', verbose_name='урок')),
                ('answered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='answered_student_questions', to=settings.AUTH_USER_MODEL, verbose_name='ответил')),
            ],
            options={
                'verbose_name': 'вопрос ученика',
                'verbose_name_plural': 'вопросы учеников',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='studentquestion',
            index=models.Index(fields=['student', '-created_at'], name='student_questions_idx'),
        ),
        migrations.AddIndex(
            model_name='studentquestion',
            index=models.Index(fields=['quality', 'created_at'], name='question_quality_idx'),
        ),
    ]
