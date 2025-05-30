import os
import logging
from telethon import TelegramClient

from bot.config import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_FOLDER, LOGGING_LEVEL, LOGGING_FORMAT, MAX_RETRIES, RETRY_DELAY, MAX_FILE_SIZE
from bot.handlers import register_handlers

log = logging.getLogger(__name__)

def initialize_bot():
    # Setup logging
    logging.basicConfig(
        level=LOGGING_LEVEL,
        format=LOGGING_FORMAT
    )

    # Ensure download folder exists
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    # Initialize client
    client = TelegramClient('userbot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    
    # Register handlers
    register_handlers(client)

    return client

def run_bot(client: TelegramClient):
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

if __name__ == '__main__':
    # This block is typically not run directly in a modular setup
    # It's here for direct testing if desired, but main_runner.py is the intended entry
    bot_client = initialize_bot()
    run_bot(bot_client)