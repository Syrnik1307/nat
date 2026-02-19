# Generated migration for chat analytics and activity tracking

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0019_increase_zoom_url_length'),
        ('accounts', '0023_ref_url_max_length'),
    ]

    operations = [
        # Новые поля для Message
        migrations.AddField(
            model_name='message',
            name='message_type',
            field=models.CharField(choices=[('text', 'Текст'), ('question', 'Вопрос'), ('answer', 'Ответ на вопрос'), ('file', 'Файл'), ('system', 'Системное')], default='text', max_length=20, verbose_name='Тип сообщения'),
        ),
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='accounts.message', verbose_name='Ответ на'),
        ),
        migrations.AddField(
            model_name='message',
            name='mentioned_users',
            field=models.ManyToManyField(blank=True, related_name='mentioned_in_messages', to=settings.AUTH_USER_MODEL, verbose_name='Упомянутые пользователи'),
        ),
        migrations.AddField(
            model_name='message',
            name='sentiment_score',
            field=models.FloatField(blank=True, help_text='Оценка тональности -1 (негатив) до +1 (позитив)', null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='is_helpful',
            field=models.BooleanField(blank=True, help_text='Является ли сообщение помощью другому ученику', null=True),
        ),
        # Индекс для Message
        migrations.AddIndex(
            model_name='message',
            index=models.Index(fields=['chat', 'sender', 'created_at'], name='msg_analytics_idx'),
        ),
        
        # Модель StudentActivityLog
        migrations.CreateModel(
            name='StudentActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('homework_start', 'Начал ДЗ'), ('homework_submit', 'Сдал ДЗ'), ('answer_save', 'Сохранил ответ'), ('lesson_join', 'Зашёл на урок'), ('recording_watch', 'Смотрел запись'), ('chat_message', 'Написал в чат'), ('question_ask', 'Задал вопрос'), ('login', 'Вход в систему')], max_length=30, verbose_name='тип действия')),
                ('details', models.JSONField(blank=True, default=dict, help_text='Дополнительные данные: {"homework_id": 123, "score": 85}')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('day_of_week', models.PositiveSmallIntegerField(help_text='0=Понедельник, 6=Воскресенье', verbose_name='день недели')),
                ('hour_of_day', models.PositiveSmallIntegerField(help_text='0-23', verbose_name='час дня')),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='activity_logs', to=settings.AUTH_USER_MODEL, verbose_name='ученик')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='student_activity_logs', to='schedule.group', verbose_name='группа')),
            ],
            options={
                'verbose_name': 'лог активности ученика',
                'verbose_name_plural': 'логи активности учеников',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='studentactivitylog',
            index=models.Index(fields=['student', '-created_at'], name='activity_student_idx'),
        ),
        migrations.AddIndex(
            model_name='studentactivitylog',
            index=models.Index(fields=['day_of_week', 'hour_of_day'], name='activity_heatmap_idx'),
        ),
        migrations.AddIndex(
            model_name='studentactivitylog',
            index=models.Index(fields=['action_type', 'created_at'], name='activity_type_idx'),
        ),
        
        # Модель ChatAnalyticsSummary
        migrations.CreateModel(
            name='ChatAnalyticsSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_start', models.DateField(verbose_name='начало периода')),
                ('period_end', models.DateField(verbose_name='конец периода')),
                ('total_messages', models.IntegerField(default=0, help_text='Всего сообщений')),
                ('questions_asked', models.IntegerField(default=0, help_text='Вопросов задано')),
                ('answers_given', models.IntegerField(default=0, help_text='Ответов на вопросы других')),
                ('helpful_messages', models.IntegerField(default=0, help_text='Полезных сообщений (помощь)')),
                ('times_mentioned', models.IntegerField(default=0, help_text='Сколько раз упомянули этого ученика')),
                ('times_mentioning_others', models.IntegerField(default=0, help_text='Сколько раз упоминал других')),
                ('avg_sentiment', models.FloatField(blank=True, help_text='Средний сентимент -1..+1', null=True)),
                ('positive_messages', models.IntegerField(default=0)),
                ('negative_messages', models.IntegerField(default=0)),
                ('neutral_messages', models.IntegerField(default=0)),
                ('influence_score', models.IntegerField(default=0, help_text='Индекс влиятельности: частота упоминаний + ответы на вопросы')),
                ('detected_role', models.CharField(choices=[('leader', '👑 Лидер'), ('helper', '🤝 Помощник'), ('active', '💬 Активный'), ('observer', '👀 Наблюдатель'), ('silent', '🔇 Молчун')], default='observer', help_text='Автоматически определённая роль в группе', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(limit_choices_to={'role': 'student'}, on_delete=django.db.models.deletion.CASCADE, related_name='chat_analytics', to=settings.AUTH_USER_MODEL, verbose_name='ученик')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_chat_analytics', to='schedule.group', verbose_name='группа')),
            ],
            options={
                'verbose_name': 'статистика чата ученика',
                'verbose_name_plural': 'статистика чатов учеников',
                'unique_together': {('student', 'group', 'period_start', 'period_end')},
            },
        ),
        migrations.AddIndex(
            model_name='chatanalyticssummary',
            index=models.Index(fields=['group', 'period_end'], name='chat_group_period_idx'),
        ),
        migrations.AddIndex(
            model_name='chatanalyticssummary',
            index=models.Index(fields=['influence_score'], name='chat_influence_idx'),
        ),
    ]
