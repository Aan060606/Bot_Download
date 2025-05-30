from telethon import Button

def create_main_keyboard():
    """Create main menu keyboard"""
    return [
        [Button.inline("⭐ Start", "start")],
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