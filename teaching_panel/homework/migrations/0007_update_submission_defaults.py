from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homework', '0006_add_teacher_feedback_summary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentsubmission',
            name='status',
            field=models.CharField(choices=[('in_progress', 'В процессе'), ('submitted', 'Отправлено'), ('graded', 'Проверено')], default='in_progress', max_length=20),
        ),
        migrations.AlterField(
            model_name='studentsubmission',
            name='submitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
