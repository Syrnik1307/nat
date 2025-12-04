#!/usr/bin/env python
"""Создать корневую папку TeachingPanel в Google Drive"""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def main():
    token_file = 'gdrive_token.json'
    
    if not os.path.exists(token_file):
        print(f"Ошибка: {token_file} не найден")
        return
    
    # Загрузить credentials
    creds = Credentials.from_authorized_user_file(
        token_file, 
        ['https://www.googleapis.com/auth/drive.file']
    )
    
    # Создать Google Drive service
    service = build('drive', 'v3', credentials=creds)
    
    print("Создаю корневую папку 'TeachingPanel'...\n")
    
    # Создать папку
    file_metadata = {
        'name': 'TeachingPanel',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id, name, webViewLink'
    ).execute()
    
    folder_id = folder.get('id')
    folder_name = folder.get('name')
    web_link = folder.get('webViewLink')
    
    print(f"✅ Папка создана успешно!")
    print(f"   Имя: {folder_name}")
    print(f"   ID: {folder_id}")
    print(f"   Ссылка: {web_link}")
    print()
    print(f"📋 Добавь в .env на сервере:")
    print(f"GDRIVE_ROOT_FOLDER_ID={folder_id}")

if __name__ == '__main__':
    main()
