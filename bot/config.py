import os
import logging
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Bot Configuration
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Logging Configuration
LOGGING_LEVEL = logging.WARNING # Ubah ke WARNING untuk production
LOGGING_FORMAT = '[%(asctime)s] %(levelname)s - %(message)s'

# Folder download
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "bot_downloads")

# Download and Upload Configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
CHUNK_SIZE = 64 * 1024  # 64KB
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB max for Telegram

# User states for conversation flow (shared state)
USER_STATES = {}

# Common video extensions for filename sanitization
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']