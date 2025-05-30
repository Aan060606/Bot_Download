from telethon import Button

def create_main_keyboard():
    """Buat keyboard menu utama"""
    return [
        [Button.inline("⭐ Mulai", "start")],
        [Button.inline("📥 Unduh Video", "download_video")],
        [Button.inline("📊 Status Bot", "bot_status"), Button.inline("🗑️ Bersihkan", "cleanup")],
        [Button.inline("ℹ️ Bantuan & Panduan", "help"), Button.inline("⚙️ Pengaturan", "settings")]
    ]

def create_back_keyboard():
    """Buat keyboard kembali ke menu utama"""
    return [[Button.inline("🔙 Kembali ke Menu Utama", "main_menu")]]

def create_download_keyboard():
    """Buat keyboard opsi unduhan"""
    return [
        [Button.inline("🔗 Tempel URL", "paste_url")],
        [Button.inline("📋 URL dari Clipboard", "url_clipboard")],
        [Button.inline("🔙 Kembali", "main_menu")]
    ]

def create_settings_keyboard():
    """Buat keyboard pengaturan"""
    return [
        [Button.inline("🔄 Pengaturan Percobaan Ulang", "retry_settings")],
        [Button.inline("📁 Pengaturan File", "file_settings")],
        [Button.inline("🔙 Kembali", "main_menu")]
    ]

def create_success_keyboard():
    """Buat keyboard penyelesaian sukses dengan tindakan cepat"""
    return [
        [Button.inline("📥 Unduh Video Lain", "download_video")],
        [Button.inline("🏠 Menu Utama", "main_menu")]
    ]