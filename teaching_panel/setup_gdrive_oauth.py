"""
Скрипт для получения OAuth2 токена Google Drive
Запускается ЛОКАЛЬНО для авторизации под твоим аккаунтом

Использование:
    python setup_gdrive_oauth.py

После запуска:
1. Откроется браузер для авторизации
2. Разреши доступ к Google Drive
3. Скрипт сохранит token.json
4. Загрузи token.json на сервер
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os.path
import pickle

# Scopes определяют, к чему будет доступ
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    """Получить OAuth2 credentials через браузер"""
    creds = None
    token_file = 'gdrive_token.json'
    
    print("=" * 60)
    print("Google Drive OAuth2 Setup для Teaching Panel")
    print("=" * 60)
    print()
    
    # Проверяем, есть ли уже токен
    if os.path.exists(token_file):
        print(f"✓ Найден существующий токен: {token_file}")
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            print("✓ Токен загружен")
        except Exception as e:
            print(f"✗ Ошибка загрузки токена: {e}")
            creds = None
    
    # Если токена нет или он невалиден
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("⟳ Обновляю токен...")
            try:
                creds.refresh(Request())
                print("✓ Токен обновлен")
            except Exception as e:
                print(f"✗ Не удалось обновить: {e}")
                creds = None
        
        if not creds:
            # Нужно получить новый токен
            print()
            print("⚠ Требуется авторизация")
            print()
            print("Для продолжения нужен client_secrets.json:")
            print("1. Открой https://console.cloud.google.com/apis/credentials")
            print("2. Выбери проект 'teaching-panel'")
            print("3. Создай 'OAuth 2.0 Client ID' (тип: Desktop app)")
            print("4. Скачай JSON и сохрани как 'client_secrets.json' в этой папке")
            print()
            
            secrets_file = 'client_secrets.json'
            if not os.path.exists(secrets_file):
                print(f"✗ Файл {secrets_file} не найден!")
                print(f"  Положи его в: {os.path.abspath('.')}")
                return
            
            print(f"✓ Найден {secrets_file}")
            print()
            print("Сейчас откроется браузер для авторизации...")
            print("Разреши доступ к Google Drive")
            print()
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
                print()
                print("✓ Авторизация успешна!")
            except Exception as e:
                print(f"✗ Ошибка авторизации: {e}")
                return
        
        # Сохраняем токен
        try:
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print(f"✓ Токен сохранён в: {os.path.abspath(token_file)}")
        except Exception as e:
            print(f"✗ Ошибка сохранения: {e}")
            return
    
    print()
    print("=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)
    print()
    print("Следующие шаги:")
    print(f"1. Загрузи файл {token_file} на сервер:")
    print(f"   scp {token_file} root@72.56.81.163:/var/www/teaching_panel/")
    print()
    print("2. Установи права:")
    print("   ssh root@72.56.81.163 'chmod 600 /var/www/teaching_panel/gdrive_token.json'")
    print()
    print("3. Перезапусти Django:")
    print("   ssh root@72.56.81.163 'systemctl restart teaching_panel'")
    print()

if __name__ == '__main__':
    main()
