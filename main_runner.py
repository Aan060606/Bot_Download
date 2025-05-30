import asyncio
import logging
from bot.main import start_bot
from bot.config import log, DOWNLOAD_FOLDER, MAX_RETRIES, RETRY_DELAY, MAX_FILE_SIZE

if __name__ == '__main__':
    print("🚀 ========================================")
    print("🎬 Enhanced User-Friendly Video Bot")
    print("🚀 ========================================")
    print(f"📁 Folder unduhan: {DOWNLOAD_FOLDER}")
    print(f"🔄 Maksimal percobaan ulang: {MAX_RETRIES}")
    print(f"⏱️ Penundaan percobaan ulang: {RETRY_DELAY}s")
    print(f"📏 Ukuran file maksimal: {MAX_FILE_SIZE/1024/1024:.0f}MB")
    print("🚀 ========================================")
    print("✅ Bot berjalan dengan UI yang ditingkatkan...")
    print("🎯 Pengguna sekarang dapat menggunakan tombol daripada perintah!")
    print("🚀 ========================================")

    asyncio.run(start_bot())