# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0005_merge_20260217_2240'),
        ('tenants', '0004_school_to_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='quicksupportresponse',
            name='tenant',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='quick_support_responses',
                to='tenants.tenant',
                verbose_name='Тенант',
            ),
        ),
    ]
