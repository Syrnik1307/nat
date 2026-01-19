#!/usr/bin/env python
"""
Скрипт для исправления битых URL изображений в вопросах.
Удаляет ссылки на несуществующие локальные файлы.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Question

def main():
    # Найти все вопросы с локальными путями к изображениям
    questions = Question.objects.all()
    fixed = 0
    broken = []
    
    for q in questions:
        config = q.config
        if not config or not isinstance(config, dict):
            continue
        
        image_url = config.get('imageUrl', '')
        audio_url = config.get('audioUrl', '')
        
        modified = False
        
        # Если это локальный путь /media/homework_files/...
        if image_url and image_url.startswith('/media/homework_files/'):
            # Проверяем, есть ли imageFileId с GDrive
            gdrive_id = config.get('imageFileId')
            if gdrive_id:
                # Заменяем на GDrive URL
                config['imageUrl'] = f'https://drive.google.com/uc?export=download&id={gdrive_id}'
                modified = True
                print(f"Q{q.id}: replaced with GDrive URL for imageFileId={gdrive_id}")
            else:
                # Нет GDrive ID - просто удаляем битую ссылку
                del config['imageUrl']
                modified = True
                broken.append((q.id, q.homework_id, image_url))
                print(f"Q{q.id}: removed broken local imageUrl: {image_url}")
        
        if audio_url and audio_url.startswith('/media/homework_files/'):
            gdrive_id = config.get('audioFileId')
            if gdrive_id:
                config['audioUrl'] = f'https://drive.google.com/uc?export=download&id={gdrive_id}'
                modified = True
                print(f"Q{q.id}: replaced with GDrive URL for audioFileId={gdrive_id}")
            else:
                del config['audioUrl']
                modified = True
                broken.append((q.id, q.homework_id, audio_url))
                print(f"Q{q.id}: removed broken local audioUrl: {audio_url}")
        
        if modified:
            q.config = config
            q.save(update_fields=['config'])
            fixed += 1
    
    print(f"\n=== ИТОГО ===")
    print(f"Исправлено вопросов: {fixed}")
    print(f"Удалено битых ссылок без GDrive ID: {len(broken)}")
    if broken:
        print("\nБитые ссылки (вопрос_id, homework_id, url):")
        for b in broken:
            print(f"  Q{b[0]} (HW{b[1]}): {b[2]}")


if __name__ == '__main__':
    main()
