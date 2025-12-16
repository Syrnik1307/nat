"""Минимальный smoke-тест GDrive (ручной запуск).

Не выполняется при импорте, чтобы не ломать `manage.py test`.
"""


def main():
    from schedule.gdrive_utils import get_gdrive_manager

    print("=" * 60)
    print("Testing Google Drive OAuth2 Integration")
    print("=" * 60)

    try:
        gdrive = get_gdrive_manager()
        print("✓ Google Drive Manager initialized successfully")
        print(f"✓ Root folder ID: {getattr(gdrive, 'root_folder_id', None)}")
        print("\n✅ OAuth2 is working!")
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()


if __name__ == '__main__':
    main()
