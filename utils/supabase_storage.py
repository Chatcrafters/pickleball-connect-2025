import os
import requests
from werkzeug.utils import secure_filename
import uuid

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://epebbniygmkkyqoaypro.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
BUCKET_NAME = 'pcl-photos'

def upload_photo_to_supabase(file, folder='players'):
    """
    Upload a photo to Supabase Storage
    
    Args:
        file: FileStorage object from Flask
        folder: Subfolder in bucket (e.g., 'players', 'teams')
    
    Returns:
        dict: {'success': True, 'url': '...'} or {'success': False, 'error': '...'}
    """
    if not file or not file.filename:
        return {'success': False, 'error': 'No file provided'}
    
    # Check file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext not in allowed_extensions:
        return {'success': False, 'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}
    
    # Generate unique filename
    unique_filename = f"{folder}/{uuid.uuid4().hex}.{ext}"
    
    # Upload to Supabase Storage
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{unique_filename}"
        
        headers = {
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'apikey': SUPABASE_KEY,
            'Content-Type': file.content_type or 'image/jpeg'
        }
        
        # Read file content
        file_content = file.read()
        
        response = requests.post(url, headers=headers, data=file_content)
        
        if response.status_code in [200, 201]:
            # Return public URL
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{unique_filename}"
            return {'success': True, 'url': public_url, 'filename': unique_filename}
        else:
            return {'success': False, 'error': f'Upload failed: {response.text}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_photo_from_supabase(filename):
    """
    Delete a photo from Supabase Storage
    
    Args:
        filename: Path in bucket (e.g., 'players/abc123.jpg')
    
    Returns:
        bool: Success status
    """
    if not filename:
        return False
    
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{filename}"
        
        headers = {
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'apikey': SUPABASE_KEY
        }
        
        response = requests.delete(url, headers=headers)
        return response.status_code in [200, 204]
        
    except Exception as e:
        print(f"Error deleting photo: {e}")
        return False


def get_photo_url(filename):
    """
    Get the public URL for a photo
    
    Args:
        filename: Path in bucket or full URL
    
    Returns:
        str: Public URL
    """
    if not filename:
        return None
    
    # If already a full URL, return as-is
    if filename.startswith('http'):
        return filename
    
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{filename}"