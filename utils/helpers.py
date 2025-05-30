import re
import os
from urllib.parse import urlparse
import aiohttp
import aiofiles
from bot.config import DOWNLOAD_FOLDER, log # Import log dan DOWNLOAD_FOLDER dari config bot

def sanitize_filename(filename: str) -> str:
    """Bersihkan dan perbaiki nama file dengan ekstensi yang tepat"""
    if not filename:
        return "video.mp4"
    
    # Hapus karakter ilegal untuk nama file
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace('\n', '').replace('\r', '').strip()
    
    # Ekstensi video umum
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Periksa apakah nama file sudah memiliki ekstensi yang tepat
    name_lower = filename.lower()
    has_extension = any(name_lower.endswith(ext) for ext in video_extensions)
    
    if not has_extension:
        # Coba deteksi ekstensi dari pola nama file
        for ext in video_extensions:
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
            filename += '.mp4' # Default ke .mp4 jika tidak ada ekstensi yang terdeteksi
    
    if len(filename) > 200:
        name_part = filename[:150]
        ext_part = filename[filename.rfind('.'):]
        filename = name_part + ext_part
    
    return filename

def get_extension_from_url(url: str) -> str:
    """Coba dapatkan ekstensi file dari URL"""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'jpg', 'jpeg', 'png', 'gif']: # Tambah ekstensi gambar
                return '.' + ext
    except:
        pass
    return '.mp4'

async def safe_cleanup(filepath: str):
    """Hapus file yang diunduh dengan aman beserta thumbnailnya"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ File dibersihkan: {filepath}")
        
        # Coba hapus thumbnail terkait jika ada
        thumb_path = os.path.splitext(filepath)[0] + '.jpg'
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            log.info(f"🗑️ Thumbnail dibersihkan: {thumb_path}")
            
    except Exception as e:
        log.error(f"❌ Gagal membersihkan {filepath}: {str(e)}")

async def download_thumbnail(thumbnail_url: str, filepath: str) -> str | None:
    """Mengunduh thumbnail ke folder unduhan dan mengembalikan path-nya."""
    if not thumbnail_url:
        return None

    thumb_filename = os.path.splitext(os.path.basename(filepath))[0] + '.jpg'
    thumb_filepath = os.path.join(DOWNLOAD_FOLDER, thumb_filename)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url, timeout=10) as resp:
                resp.raise_for_status()
                async with aiofiles.open(thumb_filepath, 'wb') as f:
                    await f.write(await resp.read())
        log.info(f"🖼️ Thumbnail berhasil diunduh: {thumb_filepath}")
        return thumb_filepath
    except aiohttp.ClientError as e:
        log.warning(f"❌ Gagal mengunduh thumbnail dari {thumbnail_url}: {e}")
    except Exception as e:
        log.warning(f"❌ Kesalahan saat mengunduh thumbnail {thumbnail_url}: {e}")
    return None