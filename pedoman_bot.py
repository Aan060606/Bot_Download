import os
import logging
import aiohttp
import asyncio
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError, FilePartMissingError
from dotenv import load_dotenv
import time
from poop_download import PoopDownload
from typing import Optional, Dict, Any
import aiofiles
import re
from urllib.parse import urlparse

# Load .env
load_dotenv()
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Logging
logging.basicConfig(
    level=logging.WARNING,  # Ubah ke WARNING untuk production
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Init client
client = TelegramClient('userbot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Folder download
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
CHUNK_SIZE = 64 * 1024  # 64KB
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB max for Telegram

# User states for conversation flow
user_states = {}

class DownloadError(Exception):
    pass

class UploadError(Exception):
    pass

def sanitize_filename(filename: str) -> str:
    """Sanitize and fix filename with proper extension"""
    if not filename:
        return "video.mp4"
    
    # Remove illegal characters for filename
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace('\n', '').replace('\r', '').strip()
    
    # Common video extensions
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
    
    # Check if filename already has proper extension
    name_lower = filename.lower()
    has_extension = any(name_lower.endswith(ext) for ext in video_extensions)
    
    if not has_extension:
        # Try to detect extension from filename pattern
        # Look for patterns like "filename mp4" or "filename.mp4" (with missing dot)
        for ext in video_extensions:
            ext_without_dot = ext[1:]  # Remove the dot
            
            # Pattern: "filename mp4" at the end
            if name_lower.endswith(' ' + ext_without_dot):
                filename = filename[:-len(ext_without_dot)-1] + ext
                break
            # Pattern: "filename mp4" anywhere (replace last occurrence)
            elif ' ' + ext_without_dot in name_lower:
                last_pos = name_lower.rfind(' ' + ext_without_dot)
                filename = filename[:last_pos] + ext
                break
            # Pattern: "filenamempv4" (missing space and dot)
            elif name_lower.endswith(ext_without_dot):
                filename = filename[:-len(ext_without_dot)] + ext
                break
        else:
            # If no extension detected, add .mp4 as default
            filename += '.mp4'
    
    # Ensure filename is not too long (max 255 chars for most filesystems)
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
            # Common video extensions
            if ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v']:
                return '.' + ext
    except:
        pass
    return '.mp4'  # Default extension

def create_main_keyboard():
    """Create main menu keyboard"""
    return [
        [Button.inline("⭐ Start", "start")],  # ← Tambahkan tombol Start di sini
        [Button.inline("📥 Download Video", "download_video")],
        [Button.inline("📊 Bot Status", "bot_status"), Button.inline("🗑️ Cleanup", "cleanup")],
        [Button.inline("ℹ️ Help & Guide", "help"), Button.inline("⚙️ Settings", "settings")]
    ]

def create_back_keyboard():
    """Create back to main menu keyboard"""
    return [[Button.inline("🔙 Back to Main Menu", "main_menu")]]

def create_download_keyboard():
    """Create download options keyboard"""
    return [
        [Button.inline("🔗 Paste URL", "paste_url")],
        [Button.inline("📋 URL from Clipboard", "url_clipboard")],
        [Button.inline("🔙 Back", "main_menu")]
    ]

def create_settings_keyboard():
    """Create settings keyboard"""
    return [
        [Button.inline("🔄 Retry Settings", "retry_settings")],
        [Button.inline("📁 File Settings", "file_settings")],
        [Button.inline("🔙 Back", "main_menu")]
    ]

def create_success_keyboard():
    """Create success completion keyboard with quick actions"""
    return [
        [Button.inline("📥 Download Another Video", "download_video")],
        [Button.inline("🏠 Main Menu", "main_menu")]
    ]

async def get_video_info(url: str, max_retries: int = MAX_RETRIES) -> list[dict]:
    """Get video info with retry mechanism and filename fixing"""
    for attempt in range(max_retries):
        try:
            poop = PoopDownload()
            poop.execute(url)
            result = poop.result

            if result['status'] != 'success' or not result['data']:
                raise DownloadError("Gagal parsing video dari URL")

            return result['data']  # <-- return semua video (list of dict)
        except Exception as e:
            log.warning(f"Attempt {attempt + 1}/{max_retries} failed for get_video_info: {str(e)}")
            if attempt == max_retries - 1:
                raise DownloadError(f"Gagal mendapatkan info video setelah {max_retries} percobaan: {str(e)}")
            await asyncio.sleep(RETRY_DELAY)

async def download_video_with_retry(url: str, filename: str, max_retries: int = MAX_RETRIES) -> str:
    """Download video with retry mechanism and better error handling"""
    # Ensure filename is properly sanitized
    filename = sanitize_filename(filename)
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    
    # Check if file already exists and add counter if needed
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
            
            timeout = aiohttp.ClientTimeout(total=1800)  # 30 minutes timeout
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise DownloadError(f"HTTP {resp.status}: {resp.reason}")
                    
                    total_size = int(resp.headers.get('Content-Length', 0))
                    
                    # Check file size limit
                    if total_size > MAX_FILE_SIZE:
                        raise DownloadError(f"File terlalu besar ({total_size/1024/1024:.1f}MB). Maksimal 500MB")
                    
                    log.info(f"Downloading {os.path.basename(filepath)} ({total_size/1024/1024:.1f}MB)")
                    
                    downloaded = 0
                    start_time = time.time()
                    
                    async with aiofiles.open(temp_filepath, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Progress display
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                elapsed = time.time() - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                done = int(50 * downloaded / total_size)
                                print(f"\r📥 [{os.path.basename(filepath)[:20]}...]: [{'█' * done}{'.' * (50 - done)}] {percent:.1f}% - {speed/1024:.1f} KB/s", end='')
            
            # Move temp file to final location
            os.rename(temp_filepath, filepath)
            print()  # New line after progress
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
            await cleanup_temp_file(temp_filepath)
        
        if attempt < max_retries - 1:
            log.info(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    raise DownloadError(f"Download gagal setelah {max_retries} percobaan")

async def cleanup_temp_file(filepath: str):
    """Clean up temporary file safely"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ Temp file cleaned: {filepath}")
    except Exception as e:
        log.warning(f"Failed to cleanup temp file {filepath}: {str(e)}")

async def upload_with_retry(chat_id: int, filepath: str, caption: str, max_retries: int = MAX_RETRIES) -> bool:
    """Upload file with retry mechanism"""
    
    # Check if file exists and get size
    if not os.path.exists(filepath):
        raise UploadError("File tidak ditemukan untuk upload")
    
    file_size = os.path.getsize(filepath)
    if file_size > MAX_FILE_SIZE:
        raise UploadError(f"File terlalu besar untuk Telegram ({file_size/1024/1024:.1f}MB > 500MB)")
    
    for attempt in range(max_retries):
        try:
            log.info(f"Upload attempt {attempt + 1}/{max_retries} - {os.path.basename(filepath)}")
            
            # Check for thumbnail
            thumb_path = os.path.splitext(filepath)[0] + '.jpg'
            thumb_exists = os.path.exists(thumb_path)
            
            # Upload progress tracking
            upload_start_time = time.time()
            last_progress_time = time.time()
            
            def progress_callback(current: int, total: int):
                nonlocal last_progress_time
                current_time = time.time()
                
                # Update progress every 2 seconds to avoid spam
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
                part_size_kb=512  # Smaller part size for better reliability
            )
            
            print()  # New line after progress
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

async def safe_cleanup(filepath: str):
    """Safely remove downloaded file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            log.info(f"🗑️ File cleaned up: {filepath}")
        
        # Also try to remove thumbnail if exists
        thumb_path = os.path.splitext(filepath)[0] + '.jpg'
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
            log.info(f"🗑️ Thumbnail cleaned up: {thumb_path}")
            
    except Exception as e:
        log.error(f"❌ Failed to cleanup {filepath}: {str(e)}")

async def process_video_download(chat_id: int, url: str, status_msg):
    filepaths = []
    try:
        video_infos = await get_video_info(url)
        if not isinstance(video_infos, list):
            video_infos = [video_infos]

        total = len(video_infos)
        for idx, video_info in enumerate(video_infos, 1):
            await status_msg.edit(
                f"📥 **[{idx}/{total}] Downloading:** `{video_info['filename']}`\n"
                f"📊 **Size:** {video_info.get('size', 'Unknown')}\n"
                f"⏱️ **Duration:** {video_info.get('duration', 'Unknown')}\n\n"
                f"Progress: **{idx}/{total}**\n"
                f"Please wait...",
                buttons=create_back_keyboard()
            )

            try:
                filepath = await download_video_with_retry(video_info['video_url'], video_info['filename'])
                filepaths.append(filepath)
            except DownloadError as e:
                await status_msg.edit(f"❌ **Download Failed**\n\n{str(e)}", buttons=create_back_keyboard())
                continue

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            video_title = os.path.splitext(os.path.basename(filepath))[0]
            caption = (
                f"🎬 **{video_title}**\n\n"
                f"💾 **File Size:** {file_size_mb:.1f} MB\n"
                f"⏱️ **Duration:** {video_info.get('duration', 'Unknown')}\n"
                f"📊 **Original Size:** {video_info.get('size', 'Unknown')}\n\n"
                f"📁 **Original filename:** `{video_info.get('original_filename', 'N/A')}`\n\n"
                f"🤖 **Downloaded with VideoBot**"
            )

            try:
                await upload_with_retry(chat_id, filepath, caption)
            except UploadError as e:
                await status_msg.edit(f"❌ **Upload Failed**\n\n{str(e)}", buttons=create_back_keyboard())
                continue

        await status_msg.edit(
            f"🎉 **Semua video selesai dikirim!**\n\n"
            f"Silakan cek video di bawah ini.",
            buttons=None
        )
        await client.send_message(
            chat_id,
            f"🔗 **Ingin download video lain?**\nKlik 'Download Video' untuk paste link baru, atau pilih menu lain.",
            buttons=create_main_keyboard()
        )
    except Exception as e:
        log.error(f"❌ Unexpected error: {str(e)}")
        await status_msg.edit(f"❌ **Unexpected Error**\n\n{str(e)}", buttons=create_back_keyboard())
    finally:
        # Cleanup semua file yang sudah di-download
        for filepath in filepaths:
            await safe_cleanup(filepath)

# ========== EVENT HANDLERS ==========

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Welcome message with main menu"""
    welcome_text = (
        f"🎬 **Welcome to Enhanced Video Bot!**\n\n"
        f"👋 Hello {event.sender.first_name}!\n\n"
        f"🚀 **What I can do:**\n"
        f"• 📥 Download videos from various platforms\n"
        f"• 🔧 Auto-fix corrupted filenames\n"
        f"• 📱 User-friendly interface\n"
        f"• ⚡ Fast & reliable downloads\n\n"
        f"**Choose an option below to get started:**"
    )
    
    await event.reply(welcome_text, buttons=create_main_keyboard())

@client.on(events.CallbackQuery)
async def callback_handler(event):
    """Handle all callback queries"""
    data = event.data.decode('utf-8')
    chat_id = event.chat_id
    user_id = event.sender_id

    if data == "start":  # ← Handler untuk tombol Start
        welcome_text = (
            f"🎬 **Welcome to Enhanced Video Bot!**\n\n"
            f"👋 Hello {event.sender.first_name}!\n\n"
            f"🚀 **What I can do:**\n"
            f"• 📥 Download videos from various platforms\n"
            f"• 🔧 Auto-fix corrupted filenames\n"
            f"• 📱 User-friendly interface\n"
            f"• ⚡ Fast & reliable downloads\n\n"
            f"**Choose an option below to get started:**"
        )
        await event.edit(welcome_text, buttons=create_main_keyboard())
        return

    if data == "main_menu":
        await event.edit(
            f"🎬 **Video Bot Main Menu**\n\n"
            f"Welcome back! Choose what you'd like to do:",
            buttons=create_main_keyboard()
        )
    
    elif data == "download_video":
        await event.edit(
            f"📥 **Download Video**\n\n"
            f"Choose how you want to provide the video URL:",
            buttons=create_download_keyboard()
        )
    
    elif data == "paste_url":
        user_states[user_id] = "waiting_for_url"
        await event.edit(
            f"🔗 **Paste Video URL**\n\n"
            f"Please send me the video URL you want to download.\n\n"
            f"**Supported platforms:**\n"
            f"• YouTube, TikTok, Instagram\n"
            f"• Facebook, Twitter, Reddit\n"
            f"• And many more!\n\n"
            f"Just paste the URL and I'll handle the rest! 🚀",
            buttons=create_back_keyboard()
        )
    
    elif data == "url_clipboard":
        await event.answer("⚠️ Clipboard feature coming soon!", alert=True)
    
    elif data == "bot_status":
        try:
            # Count files in download folder
            file_count = len([f for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))])
            
            # Calculate folder size
            total_size = 0
            for filename in os.listdir(DOWNLOAD_FOLDER):
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            
            status_text = (
                f"📊 **Bot Status**\n\n"
                f"🟢 **Status:** Online & Ready\n"
                f"📁 **Temp files:** {file_count} files\n"
                f"💾 **Storage used:** {total_size/1024/1024:.1f} MB\n"
                f"⚙️ **Max retries:** {MAX_RETRIES}\n"
                f"⏱️ **Retry delay:** {RETRY_DELAY}s\n"
                f"📏 **Max file size:** {MAX_FILE_SIZE/1024/1024:.0f} MB\n\n"
                f"🔧 **Performance:** Optimal"
            )
            
            await event.edit(status_text, buttons=create_back_keyboard())
        except Exception as e:
            await event.edit(f"❌ **Status Check Failed**\n\n{str(e)}", buttons=create_back_keyboard())
    
    elif data == "cleanup":
        try:
            files_removed = 0
            for filename in os.listdir(DOWNLOAD_FOLDER):
                file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    files_removed += 1
            
            await event.edit(
                f"🗑️ **Cleanup Complete**\n\n"
                f"✅ **{files_removed} files** removed successfully!\n"
                f"💾 **Storage freed up**\n\n"
                f"Your bot is now running clean! 🚀",
                buttons=create_back_keyboard()
            )
            log.info(f"Manual cleanup: {files_removed} files removed")
        except Exception as e:
            await event.edit(f"❌ **Cleanup Failed**\n\n{str(e)}", buttons=create_back_keyboard())
    
    elif data == "help":
        help_text = (
            f"ℹ️ **Help & Guide**\n\n"
            f"**🚀 How to use:**\n"
            f"1️⃣ Click **Download Video**\n"
            f"2️⃣ Choose **Paste URL**\n"
            f"3️⃣ Send your video URL\n"
            f"4️⃣ Wait for download & upload\n"
            f"5️⃣ Enjoy your video! 🎉\n\n"
            f"**🔧 Features:**\n"
            f"• Auto filename fixing\n"
            f"• Progress tracking\n"
            f"• Error recovery\n"
            f"• Multiple format support\n\n"
            f"**💡 Tips:**\n"
            f"• Use original URLs (not shortened)\n"
            f"• Check file size limits\n"
            f"• Be patient with large files\n\n"
            f"**⚠️ Limits:**\n"
            f"• Max file size: 500MB\n"
            f"• Max retries: 3 times"
        )
        await event.edit(help_text, buttons=create_back_keyboard())
    
    elif data == "settings":
        await event.edit(
            f"⚙️ **Bot Settings**\n\n"
            f"Configure your bot preferences:",
            buttons=create_settings_keyboard()
        )
    
    elif data == "retry_settings":
        await event.edit(
            f"🔄 **Retry Settings**\n\n"
            f"**Current Configuration:**\n"
            f"• Max Retries: **{MAX_RETRIES}**\n"
            f"• Retry Delay: **{RETRY_DELAY}s**\n"
            f"• Chunk Size: **{CHUNK_SIZE/1024}KB**\n\n"
            f"These settings ensure reliable downloads even with unstable connections.",
            buttons=create_back_keyboard()
        )
    
    elif data == "file_settings":
        await event.edit(
            f"📁 **File Settings**\n\n"
            f"**Current Configuration:**\n"
            f"• Max File Size: **{MAX_FILE_SIZE/1024/1024:.0f}MB**\n"
            f"• Download Folder: **{DOWNLOAD_FOLDER}**\n"
            f"• Auto Cleanup: **Enabled**\n"
            f"• Filename Fix: **Enabled**\n\n"
            f"Files are automatically cleaned after upload to save space.",
            buttons=create_back_keyboard()
        )

@client.on(events.NewMessage)
async def message_handler(event):
    """Handle regular messages (URLs when in waiting state)"""
    user_id = event.sender_id
    text = event.text
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    # Check if user is waiting for URL
    if user_states.get(user_id) == "waiting_for_url":
        # Reset user state
        user_states.pop(user_id, None)
        
        # Validate URL
        if not text or not any(platform in text.lower() for platform in ['youtube', 'youtu.be', 'tiktok', 'instagram', 'facebook', 'twitter', 'reddit', 'http']):
            await event.reply(
                f"❌ **Invalid URL**\n\n"
                f"Please provide a valid video URL.\n\n"
                f"**Supported:** YouTube, TikTok, Instagram, etc.",
                buttons=create_main_keyboard()
            )
            return
        
        # Start processing
        status_msg = await event.reply(
            f"🔍 **Analyzing URL...**\n\n"
            f"🔗 **URL:** `{text[:50]}{'...' if len(text) > 50 else ''}`\n\n"
            f"Please wait while I fetch video information...",
            buttons=create_back_keyboard()
        )
        
        # Process the download
        await process_video_download(event.chat_id, text, status_msg)

# Legacy command support
@client.on(events.NewMessage(pattern=r'^/getvideo (.+)'))
async def legacy_handler(event):
    """Legacy command handler for backward compatibility"""
    url = event.pattern_match.group(1).strip()
    
    status_msg = await event.reply(
        f"🔍 **Processing Legacy Command**\n\n"
        f"🔗 **URL:** `{url[:50]}{'...' if len(url) > 50 else ''}`\n\n"
        f"Please wait...",
        buttons=create_back_keyboard()
    )
    
    await process_video_download(event.chat_id, url, status_msg)

if __name__ == '__main__':
    print("🚀 ========================================")
    print("🎬 Enhanced User-Friendly Video Bot")
    print("🚀 ========================================")
    print(f"📁 Download folder: {DOWNLOAD_FOLDER}")
    print(f"🔄 Max retries: {MAX_RETRIES}")
    print(f"⏱️ Retry delay: {RETRY_DELAY}s")
    print(f"📏 Max file size: {MAX_FILE_SIZE/1024/1024:.0f}MB")
    print("🚀 ========================================")
    print("✅ Bot is running with enhanced UI...")
    print("🎯 Users can now use buttons instead of commands!")
    print("🚀 ========================================")
    
    client.run_until_disconnected()