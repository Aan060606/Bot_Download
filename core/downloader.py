import asyncio
import os
import time
import aiohttp
import aiofiles
from bot.config import MAX_RETRIES, RETRY_DELAY, CHUNK_SIZE, MAX_FILE_SIZE, DOWNLOAD_FOLDER, log
from utils.helpers import sanitize_filename, download_thumbnail
from core.poop_scraper import PoopScraper # <-- IMPOR KELAS PoopScraper Anda

class DownloadError(Exception):
    pass

async def get_video_info(url: str, max_retries: int = MAX_RETRIES) -> list[dict]:
    """Dapatkan info video dari PoopHD dengan mekanisme percobaan ulang dan perbaikan nama file"""
    scraper = PoopScraper() # Inisialisasi scraper di sini

    for attempt in range(max_retries):
        try:
            # Karena PoopScraper.execute tidak awaitable, kita jalankan di thread pool
            # Gunakan asyncio.to_thread untuk menjalankan blocking I/O di thread terpisah
            await asyncio.to_thread(scraper.execute, url)
            result = scraper.result

            if result['status'] != 'success' or not result['data']:
                raise DownloadError("Gagal parsing video dari URL atau tidak ada data yang ditemukan.")

            # Perbaiki struktur data jika diperlukan, pastikan setiap item adalah dict
            # yang konsisten dengan ekspektasi downloader/uploader
            processed_data = []
            for item in result['data']:
                # Asumsikan 'filename' adalah nama file yang sudah benar
                # Asumsikan 'video_url' adalah URL unduhan langsung
                # Asumsikan 'thumbnail_url' adalah URL thumbnail
                processed_data.append({
                    'filename': item.get('filename'),
                    'size': item.get('size'), # Ini string, mungkin perlu dikonversi ke byte nanti jika diperlukan
                    'duration': item.get('duration'),
                    'video_url': item.get('video_url'),
                    'thumbnail_url': item.get('thumbnail_url'),
                    'original_filename': item.get('filename') # Tambahkan ini untuk caption
                })
            return processed_data

        except DownloadError as de:
            log.warning(f"Percobaan {attempt + 1}/{max_retries} gagal untuk get_video_info (DownloadError): {str(de)}")
            if attempt == max_retries - 1:
                raise DownloadError(f"Gagal mendapatkan info video setelah {max_retries} percobaan: {str(de)}")
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            log.warning(f"Percobaan {attempt + 1}/{max_retries} gagal untuk get_video_info (Umum): {str(e)}")
            if attempt == max_retries - 1:
                raise DownloadError(f"Gagal mendapatkan info video setelah {max_retries} percobaan: {str(e)}")
            await asyncio.sleep(RETRY_DELAY)


async def download_video_with_retry(url: str, filename: str, max_retries: int = MAX_RETRIES) -> str:
    """Unduh video dengan mekanisme percobaan ulang dan penanganan kesalahan yang lebih baik"""
    filename = sanitize_filename(filename)
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    # Periksa apakah file sudah ada dan tambahkan penghitung jika perlu
    counter = 1
    original_name, ext = os.path.splitext(filename)
    while os.path.exists(filepath):
        filepath = os.path.join(DOWNLOAD_FOLDER, f"{original_name}_{counter}{ext}")
        counter += 1
    
    for attempt in range(max_retries):
        temp_filepath = f"{filepath}.tmp"
        try:
            log.info(f"Percobaan {attempt + 1}/{max_retries} - Mengunduh {os.path.basename(filepath)}")
            
            timeout = aiohttp.ClientTimeout(total=1800)  # Batas waktu 30 menit
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    resp.raise_for_status() # Cek status HTTP
                    
                    total_size = int(resp.headers.get('Content-Length', 0))
                    
                    if total_size > MAX_FILE_SIZE:
                        raise DownloadError(f"File terlalu besar ({total_size/1024/1024:.1f}MB). Maksimal {MAX_FILE_SIZE/1024/1024:.0f}MB")
                    
                    log.info(f"Mengunduh {os.path.basename(filepath)} ({total_size/1024/1024:.1f}MB)")
                    
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
                                # Batasi nama file agar tidak terlalu panjang di konsol
                                display_filename = os.path.basename(filepath)
                                if len(display_filename) > 20:
                                    display_filename = display_filename[:17] + "..."
                                print(f"\r📥 [{display_filename}]: [{'█' * int(50 * downloaded / total_size)}{'.' * (50 - int(50 * downloaded / total_size))}] {percent:.1f}% - {speed/1024:.1f} KB/s", end='')
                    
            os.rename(temp_filepath, filepath)
            print()
            log.info(f"✅ Unduhan berhasil: {filepath} ({downloaded/1024/1024:.1f}MB)")
            return filepath
            
        except asyncio.TimeoutError:
            log.warning(f"Batas waktu saat mengunduh percobaan {attempt + 1}")
            await _cleanup_temp_file(temp_filepath)
        except aiohttp.ClientResponseError as e: # Tangani kesalahan HTTP spesifik
            log.warning(f"Kesalahan HTTP percobaan {attempt + 1}: {e.status} {e.message}")
            await _cleanup_temp_file(temp_filepath)
        except aiohttp.ClientError as e:
            log.warning(f"Kesalahan jaringan percobaan {attempt + 1}: {str(e)}")
            await _cleanup_temp_file(temp_filepath)
        except DownloadError as e: # Tangani kesalahan unduhan yang dibuat sendiri
            log.warning(f"Unduhan percobaan {attempt + 1} gagal (Custom): {str(e)}")
            await _cleanup_temp_file(temp_filepath)
            # Jangan coba lagi jika file terlalu besar
            if "terlalu besar" in str(e):
                raise
        except Exception as e:
            log.warning(f"Unduhan percobaan {attempt + 1} gagal (Umum): {str(e)}")
            await _cleanup_temp_file(temp_filepath)
        
        if attempt < max_retries - 1:
            log.info(f"Mencoba lagi dalam {RETRY_DELAY} detik...")
            await asyncio.sleep(RETRY_DELAY)
    
    raise DownloadError(f"Unduhan gagal setelah {max_retries} percobaan")

async def _cleanup_temp_file(filepath: str):
    """Bersihkan file sementara dengan aman (internal untuk downloader)"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ File sementara dibersihkan: {filepath}")
    except Exception as e:
        log.warning(f"Gagal membersihkan file sementara {filepath}: {str(e)}")