#!/usr/bin/env python
"""Тест API для статистики Google Drive хранилища (ручной запуск)."""


def main():
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    import django

    django.setup()

    from accounts.models import CustomUser
    from rest_framework_simplejwt.tokens import RefreshToken
    import requests
    import json

    admin = CustomUser.objects.filter(role='admin').first()
    if not admin:
        print("❌ Admin not found")
        raise SystemExit(1)

    token = str(RefreshToken.for_user(admin).access_token)

    print(f"Admin: {admin.email}")
    print(f"Token: {token[:20]}...")
    print()

    headers = {'Authorization': f'Bearer {token}'}

    print("Testing /schedule/api/storage/gdrive-stats/all/...")
    try:
        response = requests.get(
            'http://localhost:8000/schedule/api/storage/gdrive-stats/all/',
            headers=headers,
            timeout=30,
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
