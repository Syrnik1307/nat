#!/usr/bin/env python
"""
Скрипт для очистки записей из Zoom Cloud.
Находит записи у которых есть gdrive_file_id (уже загружены) и zoom_recording_id.
Удаляет их из Zoom Cloud.

Также обрабатывает записи которые застряли без gdrive_file_id - перезапускает их обработку.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

import requests
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from schedule.models import LessonRecording, Lesson

User = get_user_model()


def get_zoom_token(teacher):
    """Получает Zoom OAuth токен для учителя"""
    if not (teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret):
        return None
    
    from schedule.zoom_client import ZoomAPIClient
    client = ZoomAPIClient(
        account_id=teacher.zoom_account_id,
        client_id=teacher.zoom_client_id,
        client_secret=teacher.zoom_client_secret
    )
    return client._get_access_token()


def list_zoom_recordings(token):
    """Получает список всех записей из Zoom Cloud"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    from_date = (timezone.now() - timezone.timedelta(days=30)).strftime('%Y-%m-%d')
    to_date = timezone.now().strftime('%Y-%m-%d')
    
    url = f"https://api.zoom.us/v2/users/me/recordings?from={from_date}&to={to_date}"
    
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Ошибка: {response.status_code}")
        return None


def delete_zoom_meeting_recordings(token, meeting_id, action='trash'):
    """Удаляет ВСЕ записи для митинга"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # action=trash перемещает в корзину (можно восстановить 30 дней)
    # action=delete удаляет безвозвратно
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings?action={action}"
    
    response = requests.delete(url, headers=headers, timeout=30)
    
    if response.status_code == 204:
        return True, "удалено"
    elif response.status_code == 404:
        return True, "уже удалено"
    else:
        return False, f"код {response.status_code}"


def main():
    print("=" * 70)
    print(" ОЧИСТКА ZOOM CLOUD")
    print("=" * 70)
    
    # Находим учителей с Zoom credentials
    teachers = User.objects.filter(
        role='teacher',
        zoom_account_id__isnull=False
    ).exclude(zoom_account_id='')
    
    print(f"\nУчителей с Zoom credentials: {teachers.count()}")
    
    for teacher in teachers:
        print(f"\n{'='*70}")
        print(f"Учитель: {teacher.email}")
        print(f"{'='*70}")
        
        token = get_zoom_token(teacher)
        if not token:
            print("  Не удалось получить токен")
            continue
        
        print("  Токен получен")
        
        # Получаем записи из Zoom Cloud
        data = list_zoom_recordings(token)
        if not data:
            print("  Нет данных")
            continue
        
        meetings = data.get('meetings', [])
        total_size_gb = sum(m.get('total_size', 0) for m in meetings) / (1024**3)
        
        print(f"  Записей в Zoom Cloud: {len(meetings)} ({total_size_gb:.2f} GB)")
        
        if not meetings:
            print("  Zoom Cloud пуст")
            continue
        
        print("\n  Записи в Zoom Cloud:")
        for m in meetings:
            meeting_id = m.get('id')
            topic = m.get('topic', '')[:40]
            size_mb = m.get('total_size', 0) / (1024**2)
            start = m.get('start_time', '')[:10]
            
            # Проверяем есть ли запись в нашей БД с gdrive
            lesson = Lesson.objects.filter(zoom_meeting_id=str(meeting_id)).first()
            
            if lesson:
                # Проверяем есть ли запись в GDrive
                rec = LessonRecording.objects.filter(
                    lesson=lesson,
                    status='ready',
                    gdrive_file_id__isnull=False
                ).exclude(gdrive_file_id='').first()
                
                if rec:
                    status = "В GDrive - МОЖНО УДАЛИТЬ"
                else:
                    status = "НЕ в GDrive - нужно скачать"
            else:
                status = "Нет урока в БД"
            
            print(f"    {meeting_id} | {start} | {size_mb:7.1f}MB | {topic}")
            print(f"       -> {status}")
        
        # Удаляем записи которые уже в GDrive
        print("\n  Удаляю записи которые уже в GDrive...")
        
        deleted = 0
        for m in meetings:
            meeting_id = m.get('id')
            
            lesson = Lesson.objects.filter(zoom_meeting_id=str(meeting_id)).first()
            if not lesson:
                continue
            
            rec = LessonRecording.objects.filter(
                lesson=lesson,
                status='ready',
                gdrive_file_id__isnull=False
            ).exclude(gdrive_file_id='').first()
            
            if rec:
                success, msg = delete_zoom_meeting_recordings(token, meeting_id)
                if success:
                    print(f"    ✅ Удалено: meeting {meeting_id} ({msg})")
                    deleted += 1
                else:
                    print(f"    ❌ Ошибка: meeting {meeting_id} ({msg})")
        
        print(f"\n  Удалено записей: {deleted}")
        
        # Показываем записи которые нужно обработать
        stuck = LessonRecording.objects.filter(
            lesson__teacher=teacher,
            status='ready',
            zoom_recording_id__isnull=False
        ).exclude(
            zoom_recording_id=''
        ).filter(
            gdrive_file_id__isnull=True
        ) | LessonRecording.objects.filter(
            lesson__teacher=teacher,
            status='ready',
            zoom_recording_id__isnull=False,
            gdrive_file_id=''
        ).exclude(zoom_recording_id='')
        
        if stuck.exists():
            print(f"\n  ⚠️  Записи застрявшие без GDrive (нужно перезапустить):")
            for r in stuck:
                print(f"    ID={r.id} | zoom_rec={r.zoom_recording_id[:20]}...")
    
    print("\n" + "=" * 70)
    print(" ГОТОВО")
    print("=" * 70)


if __name__ == '__main__':
    main()
