# Generated manually - rename school to tenant in finance
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_add_school_fk_to_profile'),
        ('tenants', '0004_school_to_tenant'),
    ]

    operations = [
        migrations.RenameField(
            model_name='studentfinancialprofile',
            old_name='school',
            new_name='tenant',
        ),
        migrations.AlterField(
            model_name='studentfinancialprofile',
            name='tenant',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='financial_profiles',
                to='tenants.tenant',
                help_text='Школа',
            ),
        ),
    ]
