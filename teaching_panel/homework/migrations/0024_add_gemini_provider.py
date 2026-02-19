# Generated migration — add Gemini to ai_provider choices and update default

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homework', '0023_merge_20260217_2240'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homework',
            name='ai_provider',
            field=models.CharField(
                choices=[
                    ('none', 'Без AI'),
                    ('deepseek', 'DeepSeek'),
                    ('openai', 'OpenAI'),
                    ('gemini', 'Google Gemini'),
                ],
                default='gemini',
                help_text='Провайдер AI для проверки',
                max_length=20,
            ),
        ),
    ]
