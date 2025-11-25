"""Add profile support fields to CustomUser."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='avatar',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Base64 или URL изображения для аватара пользователя',
                verbose_name='аватар',
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='middle_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Опционально, отображается в профиле',
                max_length=150,
                verbose_name='отчество',
            ),
        ),
    ]
