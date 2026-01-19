#!/usr/bin/env python
"""
Проверка записей в Zoom Cloud и их обработка
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

import requests
from django.utils import timezone
from zoom_pool.models import ZoomAccount


def get_zoom_token():
    """Получает Zoom access token"""
    account = ZoomAccount.objects.filter(
        is_active=True,
        access_token__isnull=False
    ).first()
    
    if not account:
        print("Нет активного Zoom аккаунта")
        return None
    
    if account.token_expires_at and account.token_expires_at <= timezone.now():
        print("Обновляю истекший токен...")
        account.refresh_access_token()
    
    return account.access_token


def list_zoom_recordings(token):
    """Получает список записей из Zoom Cloud"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Получаем записи за последний месяц
    from_date = (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
    to_date = timezone.now().strftime('%Y-%m-%d')
    
    url = f"https://api.zoom.us/v2/users/me/recordings?from={from_date}&to={to_date}"
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code} - {response.text}")
        return None


def main():
    print("=" * 60)
    print("Проверка записей в Zoom Cloud")
    print("=" * 60)
    
    token = get_zoom_token()
    if not token:
        return
    
    print("Токен получен, запрашиваю записи...")
    
    data = list_zoom_recordings(token)
    if not data:
        return
    
    meetings = data.get('meetings', [])
    total_size = data.get('total_records', 0)
    
    print(f"\nНайдено митингов с записями: {len(meetings)}")
    print(f"Общий размер: {sum(m.get('total_size', 0) for m in meetings) / (1024**3):.2f} GB")
    print("-" * 60)
    
    for meeting in meetings:
        meeting_id = meeting.get('id')
        topic = meeting.get('topic', 'Без названия')
        total_size_mb = meeting.get('total_size', 0) / (1024**2)
        start_time = meeting.get('start_time', '')
        
        print(f"\nMeeting ID: {meeting_id}")
        print(f"  Тема: {topic}")
        print(f"  Дата: {start_time}")
        print(f"  Размер: {total_size_mb:.1f} MB")
        
        files = meeting.get('recording_files', [])
        for f in files:
            file_id = f.get('id', '')
            file_type = f.get('file_type', '')
            file_size = f.get('file_size', 0) / (1024**2)
            status = f.get('status', '')
            print(f"    - {file_type}: {file_size:.1f} MB (status={status}, id={file_id[:20]}...)")


if __name__ == '__main__':
    main()
