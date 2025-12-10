import sys
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')

# Читаем файл
with open('/var/www/teaching_panel/teaching_panel/schedule/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим место для вставки mock кода
old_code = """                zoom_account.acquire()

                meeting_data = my_zoom_api_client.create_meeting(
                    user_id=zoom_account.zoom_user_id or None,
                    topic=f"{lesson.group.name} - {lesson.title}",
                    start_time=lesson.start_time,
                    duration=lesson.duration(),
                    auto_record=lesson.record_lesson  # Передаём флаг автозаписи
                )"""

new_code = """                zoom_account.acquire()

                # Mock mode для тестовых аккаунтов (без реального Zoom API)
                if zoom_account.api_key == 'test_api_key' or zoom_account.zoom_user_id == 'test_zoom_user_id':
                    import uuid
                    mock_meeting_id = str(uuid.uuid4())[:10]
                    meeting_data = {
                        'id': mock_meeting_id,
                        'start_url': f'https://zoom.us/s/{mock_meeting_id}?zak=mock_token',
                        'join_url': f'https://zoom.us/j/{mock_meeting_id}',
                        'password': '123456'
                    }
                    logger.info(f"Created MOCK Zoom meeting: {mock_meeting_id} (test account {zoom_account.email})")
                else:
                    meeting_data = my_zoom_api_client.create_meeting(
                        user_id=zoom_account.zoom_user_id or None,
                        topic=f"{lesson.group.name} - {lesson.title}",
                        start_time=lesson.start_time,
                        duration=lesson.duration(),
                        auto_record=lesson.record_lesson  # Передаём флаг автозаписи
                    )"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/var/www/teaching_panel/teaching_panel/schedule/views.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Mock mode добавлен в views.py")
else:
    print("✗ Не найден код для замены")
