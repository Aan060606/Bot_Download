import os
import logging
from dotenv import load_dotenv

# Muat .env
load_dotenv()
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Logging
logging.basicConfig(
    level=logging.WARNING,  # Ubah ke WARNING untuk produksi
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

# Folder unduhan
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Konfigurasi
MAX_RETRIES = 3
RETRY_DELAY = 5  # detik
CHUNK_SIZE = 64 * 1024  # 64KB
MAX_FILE_SIZE = 500 * 1024 * 1024  # Maksimal 500MB untuk Telegram

# Status pengguna untuk alur percakapan
user_states = {}