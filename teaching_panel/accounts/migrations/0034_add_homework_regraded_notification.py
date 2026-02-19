from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0033_systemerrorevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationsettings',
            name='notify_homework_regraded',
            field=models.BooleanField(
                default=True,
                help_text='Уведомлять при переоценке/перепроверке ДЗ'
            ),
        ),
    ]
