from telethon import TelegramClient
from bot.config import API_ID, API_HASH, BOT_TOKEN, log
from bot.handlers import register_handlers

client = TelegramClient('userbot_session', API_ID, API_HASH)

async def start_bot():
    log.info("Memulai bot...")
    await client.start(bot_token=BOT_TOKEN)
    register_handlers(client) # Daftarkan handler setelah klien dimulai
    await client.run_until_disconnected()