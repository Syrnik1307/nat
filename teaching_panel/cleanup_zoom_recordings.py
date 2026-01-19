#!/usr/bin/env python
"""
Скрипт для:
1. Удаления записей из Zoom Cloud, которые уже загружены в Google Drive
2. Показа статистики записей

Запуск: python manage.py shell < cleanup_zoom_recordings.py
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

import requests
from django.utils import timezone
from schedule.models import LessonRecording
from zoom_pool.models import ZoomAccount


def get_zoom_token():
    """Получает Zoom access token"""
    account = ZoomAccount.objects.filter(
        is_active=True,
        access_token__isnull=False
    ).first()
    
    if not account:
        print("❌ Нет активного Zoom аккаунта с токеном")
        return None
    
    # Проверяем срок действия токена
    if account.token_expires_at and account.token_expires_at <= timezone.now():
        print("🔄 Обновляю истекший токен...")
        account.refresh_access_token()
    
    return account.access_token


def delete_zoom_recording(meeting_id, recording_id, token):
    """Удаляет запись из Zoom"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Пробуем удалить конкретный файл
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings/{recording_id}"
    
    try:
        response = requests.delete(url, headers=headers, timeout=30)
        
        if response.status_code == 204:
            return True, "удалено"
        elif response.status_code == 404:
            return True, "уже удалено"
        elif response.status_code == 400:
            return True, "невалидный ID (уже удалено?)"
        else:
            # Пробуем перенести в корзину всю запись митинга
            url_trash = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings?action=trash"
            resp_trash = requests.delete(url_trash, headers=headers, timeout=30)
            if resp_trash.status_code in [204, 404]:
                return True, "перемещено в корзину"
            return False, f"ошибка {response.status_code}: {response.text[:100]}"
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 60)
    print("🧹 Очистка записей Zoom Cloud")
    print("=" * 60)
    
    # Получаем все готовые записи с zoom_recording_id
    recordings = LessonRecording.objects.filter(
        status='ready',
        gdrive_file_id__isnull=False,
    ).exclude(
        gdrive_file_id=''
    ).exclude(
        zoom_recording_id=''
    ).exclude(
        zoom_recording_id__isnull=True
    ).select_related('lesson')
    
    total = recordings.count()
    print(f"\n📊 Найдено записей для очистки: {total}")
    
    if total == 0:
        print("✅ Нечего очищать - все записи уже удалены из Zoom")
        return
    
    # Показываем список
    print("\nЗаписи для удаления из Zoom:")
    print("-" * 60)
    
    for rec in recordings:
        size_mb = (rec.file_size or 0) / (1024**2)
        meeting_id = rec.lesson.zoom_meeting_id if rec.lesson else None
        print(f"  ID={rec.id} | Size={size_mb:.1f}MB | Meeting={meeting_id} | ZoomRec={rec.zoom_recording_id[:20]}...")
    
    print("-" * 60)
    
    # Получаем токен
    token = get_zoom_token()
    if not token:
        print("❌ Не удалось получить токен Zoom")
        return
    
    print(f"\n🔑 Токен получен")
    print("\n🗑️ Начинаю удаление из Zoom Cloud...\n")
    
    success_count = 0
    fail_count = 0
    
    for rec in recordings:
        meeting_id = rec.lesson.zoom_meeting_id if rec.lesson else None
        
        if not meeting_id:
            print(f"  ⏭️  ID={rec.id}: нет meeting_id, пропускаю")
            continue
        
        success, message = delete_zoom_recording(meeting_id, rec.zoom_recording_id, token)
        
        if success:
            print(f"  ✅ ID={rec.id}: {message}")
            # Очищаем zoom_recording_id чтобы не пытаться удалить повторно
            rec.zoom_recording_id = ''
            rec.save(update_fields=['zoom_recording_id'])
            success_count += 1
        else:
            print(f"  ❌ ID={rec.id}: {message}")
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Успешно удалено: {success_count}")
    print(f"❌ Ошибок: {fail_count}")
    print("=" * 60)


if __name__ == '__main__':
    main()
