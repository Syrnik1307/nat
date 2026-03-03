# Generated migration — add QuestionAttachment model for file attachments on questions

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('homework', '0024_add_gemini_provider'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_name', models.CharField(max_length=255, verbose_name='Имя файла')),
                ('mime_type', models.CharField(max_length=100, verbose_name='MIME-тип')),
                ('size', models.PositiveIntegerField(verbose_name='Размер (байт)')),
                ('gdrive_file_id', models.CharField(db_index=True, max_length=100, verbose_name='Google Drive File ID')),
                ('gdrive_url', models.URLField(blank=True, max_length=500, verbose_name='Google Drive URL')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')),
                ('question', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='homework.question',
                    verbose_name='Вопрос',
                )),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='uploaded_attachments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Загрузил',
                )),
            ],
            options={
                'verbose_name': 'вложение вопроса',
                'verbose_name_plural': 'вложения вопросов',
                'ordering': ['created_at'],
            },
        ),
    ]
