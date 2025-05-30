import os
import asyncio
import re  # <<< PASTIKAN BARIS INI ADA DI SINI
from telethon import events, TelegramClient
from telethon.errors.rpcerrorlist import MessageNotModifiedError  # Tambahkan error handling
from bot.keyboards import create_main_keyboard, create_back_keyboard, create_download_keyboard, create_settings_keyboard, create_success_keyboard
from bot.config import user_states, log, DOWNLOAD_FOLDER, MAX_RETRIES, RETRY_DELAY, MAX_FILE_SIZE
from core.downloader import get_video_info, download_video_with_retry, DownloadError
from core.uploader import upload_with_retry, UploadError
from utils.helpers import safe_cleanup, download_thumbnail

async def process_video_download(client: TelegramClient, chat_id: int, url: str, status_msg):
    filepaths = []
    thumbnails_paths = [] # List untuk menyimpan path thumbnail yang diunduh
    try:
        video_infos = await get_video_info(url)
        if not video_infos: # Jika tidak ada info video yang ditemukan
            await status_msg.edit(
                f"❌ **Tidak dapat menemukan info video**\n\n"
                f"URL mungkin tidak valid atau tidak didukung oleh bot saat ini.",
                buttons=create_back_keyboard()
            )
            return

        total = len(video_infos)
        for idx, video_info in enumerate(video_infos, 1):
            await status_msg.edit(
                f"📥 **[{idx}/{total}] Menganalisis & Mengunduh:**\n\n"
                f"🎬 **Judul:** `{video_info.get('filename', 'Tidak Diketahui')}`\n"
                f"📊 **Ukuran:** {video_info.get('size', 'Tidak Diketahui')}\n"
                f"⏱️ **Durasi:** {video_info.get('duration', 'Tidak Diketahui')}\n\n"
                f"Progress: **{idx}/{total}**\n"
                f"Mohon tunggu...",
                buttons=create_back_keyboard()
            )

            filepath = None
            thumbnail_path = None
            try:
                # Unduh thumbnail terlebih dahulu
                if video_info.get('thumbnail_url'):
                    thumbnail_path = await download_thumbnail(video_info['thumbnail_url'], os.path.join(DOWNLOAD_FOLDER, video_info['filename']))
                    if thumbnail_path:
                        thumbnails_paths.append(thumbnail_path)

                filepath = await download_video_with_retry(video_info['video_url'], video_info['filename'])
                filepaths.append(filepath)
            except DownloadError as e:
                log.error(f"❌ Unduhan atau thumbnail gagal untuk {video_info.get('filename')}: {str(e)}")
                await status_msg.edit(f"❌ **Unduhan Gagal**\n\n{str(e)}", buttons=create_back_keyboard())
                continue # Lanjut ke video berikutnya jika ada

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            video_title = os.path.splitext(os.path.basename(filepath))[0]
            caption = (
                f"🎬 **{video_title}**\n\n"
                f"💾 **Ukuran File:** {file_size_mb:.1f} MB\n"
                f"⏱️ **Durasi:** {video_info.get('duration', 'Tidak Diketahui')}\n"
                f"📊 **Ukuran Asli:** {video_info.get('size', 'Tidak Diketahui')}\n\n"
                f"📁 **Nama file asli:** `{video_info.get('original_filename', 'N/A')}`\n\n"
                f"🤖 **Diunduh dengan VideoBot**"
            )

            try:
                await upload_with_retry(client, chat_id, filepath, caption)
            except UploadError as e:
                log.error(f"❌ Unggahan gagal untuk {video_info.get('filename')}: {str(e)}")
                await status_msg.edit(f"❌ **Unggahan Gagal**\n\n{str(e)}", buttons=create_back_keyboard())
                continue # Lanjut ke video berikutnya jika ada

        await status_msg.edit(
            f"🎉 **Semua video selesai dikirim!**\n\n"
            f"Silakan cek video di bawah ini.",
            buttons=None # Hapus tombol setelah proses selesai
        )
        await client.send_message(
            chat_id,
            f"🔗 **Ingin mengunduh video lain?**\nKlik 'Unduh Video' untuk menempel tautan baru, atau pilih menu lain.",
            buttons=create_success_keyboard() # Berikan keyboard sukses untuk opsi cepat
        )
    except DownloadError as e:
        log.error(f"❌ Terjadi kesalahan unduhan: {str(e)}")
        await status_msg.edit(f"❌ **Kesalahan Unduhan**\n\n{str(e)}", buttons=create_back_keyboard())
    except Exception as e:
        log.error(f"❌ Terjadi kesalahan tak terduga: {str(e)}")
        await status_msg.edit(f"❌ **Kesalahan Tak Terduga**\n\n{str(e)}", buttons=create_back_keyboard())
    finally:
        for filepath in filepaths:
            await safe_cleanup(filepath)
        for thumb_path in thumbnails_paths: # Pastikan thumbnail juga dibersihkan
            await safe_cleanup(thumb_path)

def register_handlers(client: TelegramClient):
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        welcome_text = (
            f"🎬 **Selamat Datang di Enhanced Video Bot!**\n\n"
            f"👋 Halo {event.sender.first_name}!\n\n"
            f"🚀 **Apa yang bisa saya lakukan:**\n"
            f"• 📥 Mengunduh video dari berbagai platform\n"
            f"• 🔧 Memperbaiki nama file yang rusak secara otomatis\n"
            f"• 📱 Antarmuka yang ramah pengguna\n"
            f"• ⚡ Unduhan cepat & andal\n\n"
            f"**Pilih opsi di bawah untuk memulai:**"
        )
        await event.reply(welcome_text, buttons=create_main_keyboard())

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        data = event.data.decode('utf-8')
        chat_id = event.chat_id
        user_id = event.sender_id

        # Hapus state pengguna saat tombol callback diproses
        if user_id in user_states:
            user_states.pop(user_id)

        if data == "start":
            welcome_text = (
                f"🎬 **Selamat Datang di Enhanced Video Bot!**\n\n"
                f"👋 Halo {event.sender.first_name}!\n\n"
                f"🚀 **Apa yang bisa saya lakukan:**\n"
                f"• 📥 Mengunduh video dari berbagai platform\n"
                f"• 🔧 Memperbaiki nama file yang rusak secara otomatis\n"
                f"• 📱 Antarmuka yang ramah pengguna\n"
                f"• ⚡ Unduhan cepat & andal\n\n"
                f"**Pilih opsi di bawah untuk memulai:**"
            )
            try:
                await event.edit(welcome_text, buttons=create_main_keyboard())
            except MessageNotModifiedError:
                await event.answer("Anda sudah berada di menu utama.", alert=False)
            return

        if data == "main_menu":
            try:
                await event.edit(
                    f"🎬 **Menu Utama Video Bot**\n\n"
                    f"Selamat datang kembali! Pilih apa yang ingin Anda lakukan:",
                    buttons=create_main_keyboard()
                )
            except MessageNotModifiedError:
                await event.answer("Anda sudah berada di menu utama.", alert=False)
        
        elif data == "download_video":
            await event.edit(
                f"📥 **Unduh Video**\n\n"
                f"Pilih bagaimana Anda ingin menyediakan URL video:",
                buttons=create_download_keyboard()
            )
        
        elif data == "paste_url":
            user_states[user_id] = "waiting_for_url"
            await event.edit(
                f"🔗 **Tempel URL Video**\n\n"
                f"Silakan kirimkan saya URL video yang ingin Anda unduh.\n\n"
                f"**Platform yang didukung:**\n"
                f"• **PoopHD.com** (dan domain terkait seperti `poop.vin`, `poophd.pro`, dll.)\n"
                f"• Dan masih banyak lagi yang akan datang!\n\n"
                f"Cukup tempel URL dan saya akan menangani sisanya! 🚀",
                buttons=create_back_keyboard()
            )
        
        elif data == "url_clipboard":
            await event.answer("⚠️ Fitur clipboard akan segera hadir!", alert=True)
            await event.edit(event.text, buttons=create_download_keyboard()) # Kembali ke menu download
        
        elif data == "bot_status":
            try:
                # Perbarui perhitungan ukuran total file yang diunduh (termasuk thumbnail)
                total_size = 0
                for root, _, files in os.walk(DOWNLOAD_FOLDER):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        if os.path.isfile(file_path):
                            total_size += os.path.getsize(file_path)
                
                file_count = len([f for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))])

                status_text = (
                    f"📊 **Status Bot**\n\n"
                    f"🟢 **Status:** Online & Siap\n"
                    f"📁 **File sementara:** {file_count} file\n"
                    f"💾 **Penyimpanan terpakai:** {total_size/1024/1024:.1f} MB\n"
                    f"⚙️ **Maksimal percobaan ulang:** {MAX_RETRIES}\n"
                    f"⏱️ **Penundaan percobaan ulang:** {RETRY_DELAY}s\n"
                    f"📏 **Ukuran file maksimal:** {MAX_FILE_SIZE/1024/1024:.0f} MB\n\n"
                    f"🔧 **Kinerja:** Optimal"
                )
                
                await event.edit(status_text, buttons=create_back_keyboard())
            except Exception as e:
                log.error(f"Error checking bot status: {e}")
                await event.edit(f"❌ **Pemeriksaan Status Gagal**\n\n{str(e)}", buttons=create_back_keyboard())
        
        elif data == "cleanup":
            try:
                files_removed = 0
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        files_removed += 1
                
                await event.edit(
                    f"🗑️ **Pembersihan Selesai**\n\n"
                    f"✅ **{files_removed} file** berhasil dihapus!\n"
                    f"💾 **Penyimpanan telah dibebaskan**\n\n"
                    f"Bot Anda sekarang berjalan bersih! 🚀",
                    buttons=create_back_keyboard()
                )
                log.info(f"Pembersihan manual: {files_removed} file dihapus")
            except Exception as e:
                log.error(f"Error during cleanup: {e}")
                await event.edit(f"❌ **Pembersihan Gagal**\n\n{str(e)}", buttons=create_back_keyboard())
        
        elif data == "help":
            help_text = (
                f"ℹ️ **Bantuan & Panduan**\n\n"
                f"**🚀 Cara menggunakan:**\n"
                f"1️⃣ Klik **Unduh Video**\n"
                f"2️⃣ Pilih **Tempel URL**\n"
                f"3️⃣ Kirim URL video Anda\n"
                f"4️⃣ Tunggu unduhan & unggahan\n"
                f"5️⃣ Nikmati video Anda! 🎉\n\n"
                f"**🔧 Fitur:**\n"
                f"• Unduh dari **PoopHD.com** (dan domain terkait)\n"
                f"• Perbaikan nama file otomatis\n"
                f"• Pelacakan progres\n"
                f"• Pemulihan kesalahan\n"
                f"• Dukungan berbagai format\n"
                f"• **Unduh Thumbnail Otomatis**\n\n"
                f"**💡 Tips:**\n"
                f"• Gunakan URL asli (bukan yang diperpendek)\n"
                f"• Periksa batas ukuran file\n"
                f"• Bersabarlah dengan file besar\n\n"
                f"**⚠️ Batasan:**\n"
                f"• Ukuran file maksimal: {MAX_FILE_SIZE/1024/1024:.0f}MB\n"
                f"• Maksimal percobaan ulang: {MAX_RETRIES} kali"
            )
            await event.edit(help_text, buttons=create_back_keyboard())
        
        elif data == "settings":
            await event.edit(
                f"⚙️ **Pengaturan Bot**\n\n"
                f"Konfigurasi preferensi bot Anda:",
                buttons=create_settings_keyboard()
            )
        
        elif data == "retry_settings":
            await event.edit(
                f"🔄 **Pengaturan Percobaan Ulang**\n\n"
                f"**Konfigurasi Saat Ini:**\n"
                f"• Maksimal Percobaan Ulang: **{MAX_RETRIES}**\n"
                f"• Penundaan Percobaan Ulang: **{RETRY_DELAY}s**\n"
                f"• Ukuran Chunk: **{CHUNK_SIZE/1024}KB**\n\n"
                f"Pengaturan ini memastikan unduhan yang andal bahkan dengan koneksi yang tidak stabil.",
                buttons=create_back_keyboard()
            )
        
        elif data == "file_settings":
            await event.edit(
                f"📁 **Pengaturan File**\n\n"
                f"**Konfigurasi Saat Ini:**\n"
                f"• Ukuran File Maksimal: **{MAX_FILE_SIZE/1024/1024:.0f}MB**\n"
                f"• Folder Unduhan: **{DOWNLOAD_FOLDER}**\n"
                f"• Pembersihan Otomatis: **Diaktifkan**\n"
                f"• Perbaikan Nama File: **Diaktifkan**\n"
                f"• Unduhan Thumbnail: **Diaktifkan**\n\n"
                f"File secara otomatis dibersihkan setelah diunggah untuk menghemat ruang.",
                buttons=create_back_keyboard()
            )
        elif data == "download_video_again": # Tambahkan handler untuk tombol 'Unduh Video Lain'
            user_states[user_id] = "waiting_for_url"
            await event.edit(
                f"🔗 **Tempel URL Video**\n\n"
                f"Silakan kirimkan saya URL video yang ingin Anda unduh.",
                buttons=create_back_keyboard()
            )

    @client.on(events.NewMessage)
    async def message_handler(event):
        user_id = event.sender_id
        text = event.text
        
        if text.startswith('/'):
            return # Abaikan perintah, karena sudah ditangani oleh handler /start

        if user_states.get(user_id) == "waiting_for_url":
            user_states.pop(user_id, None) # Hapus state setelah URL diterima
            
            # Periksa apakah URL tampak seperti URL
            if not text or not re.match(r'https?://(?:www\.)?[\w.-]+\.\w+/\S*', text):
                await event.reply(
                    f"❌ **URL Tidak Valid**\n\n"
                    f"Harap berikan URL video yang valid.\n\n"
                    f"**Didukung:** PoopHD.com dan domain terkait.",
                    buttons=create_main_keyboard()
                )
                return
            
            status_msg = await event.reply(
                f"🔍 **Menganalisis URL...**\n\n"
                f"🔗 **URL:** `{text[:50]}{'...' if len(text) > 50 else ''}`\n\n"
                f"Mohon tunggu saat saya mengambil informasi video...",
                buttons=create_back_keyboard()
            )
            
            await process_video_download(client, event.chat_id, text, status_msg)
            
    # Hapus handler /getvideo lama jika Anda sudah menggunakan UI berbasis tombol
    # Jika Anda ingin tetap mendukungnya, pastikan process_video_download berfungsi dengan baik
    # @client.on(events.NewMessage(pattern=r'^/getvideo (.+)'))
    # async def legacy_handler(event):
    #     url = event.pattern_match.group(1).strip()
    #     status_msg = await event.reply(
    #         f"🔍 **Memproses Perintah Lama**\n\n"
    #         f"🔗 **URL:** `{url[:50]}{'...' if len(url) > 50 else ''}`\n\n"
    #         f"Mohon tunggu...",
    #         buttons=create_back_keyboard()
    #     )
    #     await process_video_download(client, event.chat_id, url, status_msg)
