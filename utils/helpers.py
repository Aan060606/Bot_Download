import os
import re
import logging
from urllib.parse import urlparse
from bot.config import VIDEO_EXTENSIONS # Import from config

log = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """Sanitize and fix filename with proper extension"""
    if not filename:
        return "video.mp4"
    
    # Remove illegal characters for filename
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace('\n', '').replace('\r', '').strip()
    
    # Check if filename already has proper extension
    name_lower = filename.lower()
    has_extension = any(name_lower.endswith(ext) for ext in VIDEO_EXTENSIONS)
    
    if not has_extension:
        # Try to detect extension from filename pattern
        for ext in VIDEO_EXTENSIONS:
            ext_without_dot = ext[1:]
            
            if name_lower.endswith(' ' + ext_without_dot):
                filename = filename[:-len(ext_without_dot)-1] + ext
                break
            elif ' ' + ext_without_dot in name_lower:
                last_pos = name_lower.rfind(' ' + ext_without_dot)
                filename = filename[:last_pos] + ext
                break
            elif name_lower.endswith(ext_without_dot):
                filename = filename[:-len(ext_without_dot)] + ext
                break
        else:
            filename += '.mp4'
    
    if len(filename) > 200:
        name_part = filename[:150]
        ext_part = filename[filename.rfind('.'):]
        filename = name_part + ext_part
    
    return filename

def get_extension_from_url(url: str) -> str:
    """Try to get file extension from URL"""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in [e.replace('.', '') for e in VIDEO_EXTENSIONS]: # Check against extensions without dot
                return '.' + ext
    except:
        pass
    return '.mp4'

async def cleanup_temp_file(filepath: str):
    """Clean up temporary file safely"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ Temp file cleaned: {filepath}")
    except Exception as e:
        log.warning(f"Failed to cleanup temp file {filepath}: {str(e)}")

async def safe_cleanup(filepath: str):
    """Safely remove downloaded file and its thumbnail"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ File cleaned up: {filepath}")
        
        thumb_path = os.path.splitext(filepath)[0] + '.jpg'
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            log.info(f"🗑️ Thumbnail cleaned up: {thumb_path}")
            
    except Exception as e:
        log.error(f"❌ Failed to cleanup {filepath}: {str(e)}")