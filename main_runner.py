import os
import sys

# Add project root to sys.path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

from bot.main import initialize_bot, run_bot

if __name__ == '__main__':
    bot_client = initialize_bot()
    run_bot(bot_client)