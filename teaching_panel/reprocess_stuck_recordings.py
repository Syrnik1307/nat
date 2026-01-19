#!/usr/bin/env python
"""
Перезапуск обработки застрявших записей.
Скачивает с Zoom, сжимает через FFmpeg, загружает в GDrive, удаляет из Zoom.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording
from schedule.tasks import process_zoom_recording


def main():
    print("=" * 70)
    print(" ПЕРЕЗАПУСК ОБРАБОТКИ ЗАПИСЕЙ")
    print("=" * 70)
    
    # Находим записи с zoom_recording_id но без gdrive_file_id
    stuck = LessonRecording.objects.filter(
        zoom_recording_id__isnull=False,
    ).exclude(
        zoom_recording_id=''
    ).filter(
        gdrive_file_id__isnull=True
    ) | LessonRecording.objects.filter(
        zoom_recording_id__isnull=False,
        gdrive_file_id=''
    ).exclude(zoom_recording_id='')
    
    # Также проверим записи с gdrive_file_id=''
    stuck2 = LessonRecording.objects.filter(
        zoom_recording_id__isnull=False
    ).exclude(
        zoom_recording_id=''
    )
    
    stuck = [r for r in stuck2 if not r.gdrive_file_id]
    
    print(f"\nЗастрявших записей: {len(stuck)}")
    
    if not stuck:
        print("Нет записей для перезапуска")
        return
    
    for rec in stuck:
        size_mb = (rec.file_size or 0) / (1024**2)
        lesson_id = rec.lesson_id if rec.lesson else 'N/A'
        print(f"\n  ID={rec.id} | Lesson={lesson_id} | Size={size_mb:.1f}MB")
        print(f"    zoom_recording_id: {rec.zoom_recording_id}")
        print(f"    download_url: {rec.download_url[:50] if rec.download_url else 'N/A'}...")
        
        # Устанавливаем статус processing и запускаем задачу
        rec.status = 'processing'
        rec.save(update_fields=['status'])
        
        print(f"    Запускаю process_zoom_recording({rec.id})...")
        
        # Запускаем синхронно (не через Celery) чтобы видеть вывод
        try:
            process_zoom_recording(rec.id)
            
            # Проверяем результат
            rec.refresh_from_db()
            if rec.gdrive_file_id:
                print(f"    ✅ Успешно! GDrive file: {rec.gdrive_file_id}")
            else:
                print(f"    ❌ Ошибка: gdrive_file_id пуст, status={rec.status}")
        except Exception as e:
            print(f"    ❌ Исключение: {e}")
    
    print("\n" + "=" * 70)
    print(" ГОТОВО")
    print("=" * 70)


if __name__ == '__main__':
    main()
