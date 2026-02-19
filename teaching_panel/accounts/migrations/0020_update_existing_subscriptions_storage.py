# Generated manually: update existing subscriptions to 10GB base storage

from django.db import migrations


def set_base_storage_10gb(apps, schema_editor):
    """Update all existing subscriptions to have base_storage_gb = 10"""
    Subscription = apps.get_model('accounts', 'Subscription')
    updated = Subscription.objects.filter(base_storage_gb__lt=10).update(base_storage_gb=10)
    print(f"\n  Updated {updated} subscriptions to base_storage_gb=10")


def reverse_migration(apps, schema_editor):
    """Reverse: set back to 5 (previous default)"""
    Subscription = apps.get_model('accounts', 'Subscription')
    Subscription.objects.filter(base_storage_gb=10).update(base_storage_gb=5)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_set_base_storage_10gb'),
    ]

    operations = [
        migrations.RunPython(set_base_storage_10gb, reverse_migration),
    ]
