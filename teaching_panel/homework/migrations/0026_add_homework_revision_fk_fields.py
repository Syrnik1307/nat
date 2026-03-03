# Migration to add revision FK fields to Homework model (production fix)
# These fields are used in views.py but were never migrated on production.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('homework', '0025_add_question_attachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='homework',
            name='revision_of',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='revisions',
                to='homework.homework',
                help_text='Оригинальное ДЗ, из которого создана доработка',
            ),
        ),
        migrations.AddField(
            model_name='homework',
            name='revision_for_student',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='revision_homeworks',
                to=settings.AUTH_USER_MODEL,
                limit_choices_to={'role': 'student'},
                help_text='Ученик, для которого создана доработка',
            ),
        ),
        migrations.AddField(
            model_name='homework',
            name='revision_comment',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Комментарий учителя при отправке на доработку',
            ),
        ),
    ]
