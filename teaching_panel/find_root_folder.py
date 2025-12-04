#!/usr/bin/env python
"""Найти корневую папку TeachingPanel в Google Drive"""
import os
import sys
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
    
    print("Ищу папку 'TeachingPanel' в Google Drive...\n")
    
    # Поиск папки TeachingPanel
    results = service.files().list(
        q="name='TeachingPanel' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name, parents, createdTime)',
        pageSize=10
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        print(f"✅ Найдено папок с именем 'TeachingPanel': {len(items)}\n")
        for idx, item in enumerate(items, 1):
            print(f"{idx}. Имя: {item['name']}")
            print(f"   ID: {item['id']}")
            print(f"   Создана: {item.get('createdTime', 'N/A')}")
            if 'parents' in item:
                print(f"   Родительская папка: {item['parents'][0]}")
            else:
                print(f"   Родительская папка: Корень My Drive")
            print()
        
        # Если папка одна - предложить использовать её
        if len(items) == 1:
            folder_id = items[0]['id']
            print(f"📋 Скопируй этот ID для .env файла:")
            print(f"GDRIVE_ROOT_FOLDER_ID={folder_id}")
    else:
        print("❌ Папка 'TeachingPanel' не найдена")
        print("\nИщу все папки в корне...")
        
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name, createdTime)',
            pageSize=20,
            orderBy='createdTime desc'
        ).execute()
        
        items = results.get('files', [])
        if items:
            print(f"\nНайдено папок: {len(items)}\n")
            for idx, item in enumerate(items[:10], 1):
                print(f"{idx}. {item['name']} (ID: {item['id']})")
        else:
            print("Папок не найдено. Создай папку 'TeachingPanel' в Google Drive.")

if __name__ == '__main__':
    main()
