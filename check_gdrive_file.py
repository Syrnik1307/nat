from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()
file_id = '1mPf055he1QU0dZ_Cgz8Okp6YtWzuPRE0'

try:
    file_info = gdrive.service.files().get(
        fileId=file_id, 
        fields='id,name,size,mimeType,videoMediaMetadata'
    ).execute()
    
    print(f"File: {file_info.get('name')}")
    print(f"Size: {int(file_info.get('size', 0)) / (1024*1024):.1f} MB")
    
    meta = file_info.get('videoMediaMetadata', {})
    if meta:
        duration_ms = int(meta.get('durationMillis', 0))
        print(f"Duration: {duration_ms / 1000:.0f} sec ({duration_ms / 1000 / 60:.1f} min)")
        print(f"Width: {meta.get('width')}")
        print(f"Height: {meta.get('height')}")
    else:
        print("No video metadata available")
        
except Exception as e:
    print(f"Error: {e}")
