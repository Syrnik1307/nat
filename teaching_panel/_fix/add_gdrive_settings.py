"""Add USE_GDRIVE_STORAGE and related settings to server's settings.py"""
import os

path = '/var/www/teaching_panel/teaching_panel/teaching_panel/settings.py'
with open(path, 'r') as f:
    content = f.read()

if 'USE_GDRIVE_STORAGE' in content:
    print('Already has GDRIVE settings')
else:
    old = """# UPLOAD LIMITS"""
    new = """# GOOGLE DRIVE CONFIGURATION
# ===
USE_GDRIVE_STORAGE = os.environ.get('USE_GDRIVE_STORAGE', '0') == '1'
GDRIVE_TOKEN_FILE = os.environ.get('GDRIVE_TOKEN_FILE', str(BASE_DIR / 'gdrive_token.json'))
GDRIVE_ROOT_FOLDER_ID = os.environ.get('GDRIVE_ROOT_FOLDER_ID', '')
GDRIVE_RECORDINGS_FOLDER_ID = os.environ.get('GDRIVE_RECORDINGS_FOLDER_ID', '')

# UPLOAD LIMITS"""
    content = content.replace(old, new, 1)
    with open(path, 'w') as f:
        f.write(content)
    print('GDRIVE settings added')
