#!/usr/bin/env python
"""Тест API через Django test client (ручной запуск)."""


def main():
    import os

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    import django

    django.setup()

    from django.test import Client
    from accounts.models import CustomUser
    from rest_framework_simplejwt.tokens import RefreshToken
    import json

    admin = CustomUser.objects.filter(role='admin').first()
    if not admin:
        print("❌ Admin not found")
        raise SystemExit(1)

    token = str(RefreshToken.for_user(admin).access_token)

    print(f"Admin: {admin.email}")
    print()

    client = Client()
    headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    print("Testing /schedule/api/storage/gdrive-stats/all/ via test client...")
    response = client.get('/schedule/api/storage/gdrive-stats/all/', **headers)

    print(f"Status: {response.status_code}")
    print(f"Response: {response.content.decode()[:1000]}")

    try:
        data = json.loads(response.content)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    except Exception:
        pass


if __name__ == '__main__':
    main()
