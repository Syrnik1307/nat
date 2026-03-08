# State-only migration: register invite_code in Django migration state.
# The actual column was already created by migration 0009 via RunPython (raw SQL).
# This migration does NOT touch the database — only syncs Django's state tracker.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0034_alter_lessonrecording_archive_key_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='group',
                    name='invite_code',
                    field=models.CharField(
                        blank=True,
                        help_text='Уникальный код для присоединения учеников к группе',
                        max_length=8,
                        null=True,
                        unique=True,
                        verbose_name='код приглашения',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
