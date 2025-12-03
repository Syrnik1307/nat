from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homework', '0004_homework_published_at_homework_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='config',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('TEXT', 'Текстовый ответ'),
                    ('SINGLE_CHOICE', 'Один вариант'),
                    ('MULTI_CHOICE', 'Несколько вариантов'),
                    ('LISTENING', 'Лисенинг'),
                    ('MATCHING', 'Сопоставление'),
                    ('DRAG_DROP', 'Перетаскивание'),
                    ('FILL_BLANKS', 'Заполнение пропусков'),
                    ('HOTSPOT', 'Хотспот на изображении'),
                ],
                max_length=20,
            ),
        ),
    ]
