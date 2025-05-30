import os
import asyncio
import time
from telethon.errors import FloodWaitError, FilePartMissingError
from telethon import TelegramClient
from bot.config import MAX_RETRIES, RETRY_DELAY, MAX_FILE_SIZE, log

class UploadError(Exception):
    pass

async def upload_with_retry(client: TelegramClient, chat_id: int, filepath: str, caption: str, max_retries: int = MAX_RETRIES) -> bool:
    """Unggah file dengan mekanisme percobaan ulang"""
    
    if not os.path.exists(filepath):
        raise UploadError("File tidak ditemukan untuk diunggah")
    
    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE:
        raise UploadError(f"File terlalu besar untuk Telegram ({file_size/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024:.0f}MB)")
    
    for attempt in range(max_retries):
        try:
            log.info(f"Percobaan unggah {attempt + 1}/{max_retries} - {os.path.basename(filepath)}")
            
            thumb_path = os.path.splitext(filepath)[0] + '.jpg'
            thumb_exists = os.path.exists(thumb_path)
            
            upload_start_time = time.time()
            last_progress_time = time.time()
            
            def progress_callback(current: int, total: int):
                nonlocal last_progress_time
                current_time = time.time()
                
                if current_time - last_progress_time >= 2 or current == total:
                    percent = (current / total) * 100
                    elapsed = current_time - upload_start_time
                    speed = current / elapsed if elapsed > 0 else 0
                    print(f"\r📤 Mengunggah: {percent:.1f}% ({current/1024/1024:.1f}/{total/1024/1024:.1f}MB) - {speed/1024:.1f} KB/s", end='')
                    last_progress_time = current_time
            
            await client.send_file(
                chat_id,
                filepath,
                caption=caption,
                thumb=thumb_path if thumb_exists else None,
                supports_streaming=True,
                progress_callback=progress_callback,
                part_size_kb=512
            )
            
            print()
            log.info(f"✅ Unggahan berhasil: {os.path.basename(filepath)}")
            return True
            
        except FloodWaitError as e:
            log.warning(f"FloodWait: perlu menunggu {e.seconds} detik")
            await asyncio.sleep(e.seconds + 1)
        except FilePartMissingError:
            log.warning(f"FilePartMissing pada percobaan {attempt + 1}, mencoba lagi...")
        except Exception as e:
            log.warning(f"Unggahan percobaan {attempt + 1} gagal: {str(e)}")
        
        if attempt < max_retries - 1:
            log.info(f"Mencoba mengunggah lagi dalam {RETRY_DELAY} detik...")
            await asyncio.sleep(RETRY_DELAY)
    
    raise UploadError(f"Unggahan gagal setelah {max_retries} percobaan")