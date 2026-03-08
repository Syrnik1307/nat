# State-only migration: register invite_code in Django migration state.
# The actual column was already created by migration 0009 via RunPython (raw SQL).
# database_operations adds the column IF it doesn't already exist (needed for
# SQLite test databases where table rebuilds by later migrations can drop it).

from django.db import migrations, models


def _ensure_invite_code_column(apps, schema_editor):
    """Add invite_code column if it's missing (safe for both PostgreSQL and SQLite)."""
    vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    if vendor == 'postgresql':
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'schedule_group' AND column_name = 'invite_code'"
        )
        if cursor.fetchone():
            return  # column already exists
        cursor.execute("ALTER TABLE schedule_group ADD COLUMN invite_code varchar(8) NULL UNIQUE")
    else:
        cursor.execute("PRAGMA table_info(schedule_group);")
        cols = [row[1] for row in cursor.fetchall()]
        if 'invite_code' in cols:
            return  # column already exists
        cursor.execute("ALTER TABLE schedule_group ADD COLUMN invite_code varchar(8)")
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS schedule_group_invite_code_key "
            "ON schedule_group(invite_code)"
        )


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
            database_operations=[
                migrations.RunPython(_ensure_invite_code_column, migrations.RunPython.noop),
            ],
        ),
    ]
