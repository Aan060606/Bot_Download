import os
import asyncio
import aiohttp
import aiofiles
import logging
import time

from telethon import TelegramClient
from telethon.errors import FloodWaitError, FilePartMissingError

from bot.config import MAX_RETRIES, RETRY_DELAY, CHUNK_SIZE, MAX_FILE_SIZE, DOWNLOAD_FOLDER
from utils.helpers import sanitize_filename, cleanup_temp_file
from core.provider.poop_download import PoopDownload # Import PoopDownload

log = logging.getLogger(__name__)

class DownloadError(Exception):
    pass

class UploadError(Exception):
    pass

async def get_video_info(url: str, max_retries: int = MAX_RETRIES) -> list[dict]:
    """Get video info with retry mechanism and filename fixing"""
    for attempt in range(max_retries):
        try:
            poop = PoopDownload()
            poop.execute(url)
            result = poop.result

            if result['status'] != 'success' or not result['data']:
                raise DownloadError("Gagal parsing video dari URL")

            return result['data']
        except Exception as e:
            log.warning(f"Attempt {attempt + 1}/{max_retries} failed for get_video_info: {str(e)}")
            if attempt == max_retries - 1:
                raise DownloadError(f"Gagal mendapatkan info video setelah {max_retries} percobaan: {str(e)}")
            await asyncio.sleep(RETRY_DELAY)

async def download_video_with_retry(url: str, filename: str, max_retries: int = MAX_RETRIES) -> str:
    """Download video with retry mechanism and better error handling"""
    filename = sanitize_filename(filename)
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    counter = 1
    original_filepath = filepath
    while os.path.exists(filepath):
        name, ext = os.path.splitext(original_filepath)
        filepath = f"{name}_{counter}{ext}"
        counter += 1
    
    for attempt in range(max_retries):
        temp_filepath = f"{filepath}.tmp"
        try:
            log.info(f"Attempt {attempt + 1}/{max_retries} - Downloading {os.path.basename(filepath)}")
            
            timeout = aiohttp.ClientTimeout(total=1800)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise DownloadError(f"HTTP {resp.status}: {resp.reason}")
                    
                    total_size = int(resp.headers.get('Content-Length', 0))
                    
                    if total_size > MAX_FILE_SIZE:
                        raise DownloadError(f"File terlalu besar ({total_size/1024/1024:.1f}MB). Maksimal {MAX_FILE_SIZE/1024/1024:.0f}MB")
                    
                    log.info(f"Downloading {os.path.basename(filepath)} ({total_size/1024/1024:.1f}MB)")
                    
                    downloaded = 0
                    start_time = time.time()
                    
                    async with aiofiles.open(temp_filepath, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                done = int(50 * downloaded / total_size)
                                print(f"\r📥 [{os.path.basename(filepath)[:20]}...]: [{'█' * done}{'.' * (50 - done)}] {percent:.1f}% - {speed/1024:.1f} KB/s", end='')
            
            os.rename(temp_filepath, filepath)
            print()
            log.info(f"✅ Download berhasil: {filepath} ({downloaded/1024/1024:.1f}MB)")
            return filepath
            
        except asyncio.TimeoutError:
            log.warning(f"Timeout saat download attempt {attempt + 1}")
            await cleanup_temp_file(temp_filepath)
        except aiohttp.ClientError as e:
            log.warning(f"Network error attempt {attempt + 1}: {str(e)}")
            await cleanup_temp_file(temp_filepath)
        except Exception as e:
            log.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_retries - 1:
            log.info(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    raise DownloadError(f"Download gagal setelah {max_retries} percobaan")

async def upload_with_retry(client: TelegramClient, chat_id: int, filepath: str, caption: str, max_retries: int = MAX_RETRIES) -> bool:
    """Upload file with retry mechanism"""
    
    if not os.path.exists(filepath):
        raise UploadError("File tidak ditemukan untuk upload")
    
    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE:
        raise UploadError(f"File terlalu besar untuk Telegram ({file_size/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024:.0f}MB)")
    
    for attempt in range(max_retries):
        try:
            log.info(f"Upload attempt {attempt + 1}/{max_retries} - {os.path.basename(filepath)}")
            
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
                    print(f"\r📤 Uploading: {percent:.1f}% ({current/1024/1024:.1f}/{total/1024/1024:.1f}MB) - {speed/1024:.1f} KB/s", end='')
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
            log.info(f"✅ Upload berhasil: {os.path.basename(filepath)}")
            return True
            
        except FloodWaitError as e:
            log.warning(f"FloodWait: need to wait {e.seconds} seconds")
            await asyncio.sleep(e.seconds + 1)
        except FilePartMissingError:
            log.warning(f"FilePartMissing on attempt {attempt + 1}, retrying...")
        except Exception as e:
            log.warning(f"Upload attempt {attempt + 1} failed: {str(e)}")
        
        if attempt < max_retries - 1:
            log.info(f"Retrying upload in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    raise UploadError(f"Upload gagal setelah {max_retries} percobaan")