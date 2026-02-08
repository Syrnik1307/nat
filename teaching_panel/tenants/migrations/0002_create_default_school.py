"""
Data migration: создание школы по умолчанию "Lectio Space".

Все существующие пользователи получают SchoolMembership 
в школу по умолчанию с сохранением своей текущей роли.
"""

from django.db import migrations


def create_default_school(apps, schema_editor):
    School = apps.get_model('tenants', 'School')
    SchoolMembership = apps.get_model('tenants', 'SchoolMembership')
    User = apps.get_model('accounts', 'CustomUser')
    
    # Найти admin/superuser как владельца
    owner = User.objects.filter(is_superuser=True).first()
    if not owner:
        owner = User.objects.filter(role='admin').first()
    if not owner:
        owner = User.objects.first()
    
    if not owner:
        # Пустая БД — пропускаем
        return
    
    # Создать школу по умолчанию
    school = School.objects.create(
        slug='lectiospace',
        name='Lectio Space',
        owner=owner,
        primary_color='#4F46E5',
        secondary_color='#7C3AED',
        is_default=True,
        is_active=True,
        max_students=10000,  # Без ограничений для основной школы
        max_groups=1000,
        max_teachers=100,
        max_storage_gb=500,
        zoom_enabled=True,
        homework_enabled=True,
        recordings_enabled=True,
        finance_enabled=True,
        telegram_bot_enabled=True,
    )
    
    # Привязать всех существующих пользователей к этой школе
    memberships = []
    for user in User.objects.all():
        # Маппинг роли User → роли в SchoolMembership
        if user == owner:
            role = 'owner'
        elif getattr(user, 'role', '') == 'admin':
            role = 'admin'
        elif getattr(user, 'role', '') == 'teacher':
            role = 'teacher'
        else:
            role = 'student'
        
        memberships.append(SchoolMembership(
            school=school,
            user=user,
            role=role,
            is_active=True,
        ))
    
    if memberships:
        SchoolMembership.objects.bulk_create(memberships)


def remove_default_school(apps, schema_editor):
    School = apps.get_model('tenants', 'School')
    School.objects.filter(slug='lectiospace', is_default=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0001_initial'),
        ('accounts', '0001_initial'),  # User model
    ]

    operations = [
        migrations.RunPython(
            create_default_school,
            remove_default_school,
        ),
    ]
