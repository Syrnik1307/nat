from schedule.gdrive_utils import get_gdrive_manager

print("=" * 60)
print("Testing Google Drive OAuth2 Integration")
print("=" * 60)

try:
    gdrive = get_gdrive_manager()
    print("✓ Google Drive Manager initialized successfully")
    print(f"✓ Root folder ID: {gdrive.root_folder_id}")
    print("\n✅ OAuth2 is working!")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
