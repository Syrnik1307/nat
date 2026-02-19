"""
Google Drive Service для загрузки/скачивания файлов вложений ДЗ.

Использует тот же GDriveManager (schedule.gdrive_utils), что и записи уроков.
Файлы вложений хранятся в подпапке «homework_attachments» внутри корневой
папки GDrive (GDRIVE_ROOT_FOLDER_ID).
"""

import io
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Кеш ID папки homework_attachments
_hw_folder_id = None


def _get_manager():
    """Возвращает singleton GDriveManager из schedule."""
    from schedule.gdrive_utils import get_gdrive_manager
    return get_gdrive_manager()


def _get_homework_root_folder():
    """Получает/создаёт подпапку homework_attachments в корне GDrive."""
    global _hw_folder_id
    if _hw_folder_id:
        return _hw_folder_id

    mgr = _get_manager()
    root = mgr.root_folder_id
    if not root:
        logger.error('GDRIVE_ROOT_FOLDER_ID не настроен — файлы будут в корне Drive')
        return None

    # Используем метод менеджера (или напрямую ищем/создаём)
    _hw_folder_id = mgr._get_or_create_subfolder('homework_attachments', root)
    logger.info('Homework attachments folder: %s', _hw_folder_id)
    return _hw_folder_id


def upload_file(file_obj, original_name: str, mime_type: str, subfolder_name=None) -> dict:
    """
    Загружает файл в Google Drive (через общий GDriveManager).

    Args:
        file_obj: файловый объект (UploadedFile)
        original_name: оригинальное имя файла
        mime_type: MIME-тип
        subfolder_name: подпапка (например 'homework_42_q_1')

    Returns:
        dict: gdrive_file_id, gdrive_url, size
    """
    mgr = _get_manager()

    # Определяем целевую папку
    hw_root = _get_homework_root_folder()
    if subfolder_name and hw_root:
        folder_id = mgr._get_or_create_subfolder(subfolder_name, hw_root)
    else:
        folder_id = hw_root

    # Загружаем через общий менеджер (поддерживает file objects)
    result = mgr.upload_file(
        file_path_or_object=file_obj,
        file_name=original_name,
        folder_id=folder_id,
        mime_type=mime_type,
    )

    file_id = result['file_id']
    gdrive_url = result.get('web_view_link') or f'https://drive.google.com/file/d/{file_id}/view'

    logger.info('HW attachment uploaded: %s (id=%s)', original_name, file_id)

    return {
        'gdrive_file_id': file_id,
        'gdrive_url': gdrive_url,
        'size': result.get('size', 0),
    }


def download_file(gdrive_file_id: str) -> tuple:
    """
    Скачивает файл из Google Drive.

    Returns:
        tuple: (bytes_content, mime_type, file_name)
    """
    from googleapiclient.http import MediaIoBaseDownload

    mgr = _get_manager()
    service = mgr.service

    try:
        file_meta = service.files().get(
            fileId=gdrive_file_id,
            fields='name, mimeType, size',
        ).execute()

        request = service.files().get_media(fileId=gdrive_file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        content = buffer.read()

        logger.info('HW attachment downloaded: %s (id=%s, size=%d)',
                     file_meta['name'], gdrive_file_id, len(content))

        return content, file_meta['mimeType'], file_meta['name']

    except Exception as e:
        logger.error('Failed to download from GDrive: id=%s — %s', gdrive_file_id, e)
        raise


def delete_file(gdrive_file_id: str) -> bool:
    """Удаляет файл из Google Drive."""
    mgr = _get_manager()
    try:
        mgr.delete_file(gdrive_file_id)
        logger.info('HW attachment deleted from GDrive: id=%s', gdrive_file_id)
        return True
    except Exception as e:
        logger.error('Failed to delete from GDrive: id=%s — %s', gdrive_file_id, e)
        return False
