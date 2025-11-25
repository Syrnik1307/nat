import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser

# Создаем admin пользователя
admin = CustomUser.objects.filter(role='admin').first()
if not admin:
    admin = CustomUser.objects.create_user(
        email='admin@school.com',
        password='Admin123',
        first_name='Admin',
        last_name='User',
        role='admin'
    )
    print(f'✅ Admin создан: {admin.email}')
    print(f'   Password: Admin123')
else:
    # Обновляем пароль существующего админа
    admin.set_password('Admin123')
    admin.save()
    print(f'✅ Admin уже существует: {admin.email}')
    print(f'   Email: admin@school.com')
    print(f'   Password обновлен: Admin123')
