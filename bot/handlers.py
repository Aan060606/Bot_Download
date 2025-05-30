import os
import logging
import asyncio
import re  # Import the regex module
from telethon import TelegramClient, events, Button

from bot.config import USER_STATES, DOWNLOAD_FOLDER, MAX_RETRIES, RETRY_DELAY, CHUNK_SIZE, MAX_FILE_SIZE
from bot.keyboards import (
    create_main_keyboard, create_back_keyboard, create_download_keyboard,
    create_settings_keyboard
)
from core.uploader import (
    get_video_info, download_video_with_retry, upload_with_retry,
    DownloadError, UploadError
)
from utils.helpers import safe_cleanup

log = logging.getLogger(__name__)

async def process_video_download(client: TelegramClient, chat_id: int, url: str, status_msg) -> bool:
    """
    Memproses unduhan dan unggahan video tunggal dari URL yang diberikan.
    Mengembalikan True jika berhasil secara keseluruhan untuk URL ini, False jika gagal.
    Pesan status (status_msg) hanya akan diedit untuk kegagalan awal parsing URL.
    Progres unduhan/unggahan per video tidak akan mengedit status_msg.
    """
    filepaths = []
    try:
        video_infos = await get_video_info(url)
        # Pastikan video_infos selalu berupa daftar, bahkan jika PoopDownload mengembalikan satu kamus
        if not isinstance(video_infos, list):
            video_infos = [video_infos]

        total_videos_in_url = len(video_infos)
        successful_uploads_for_url = 0

        for idx, video_info in enumerate(video_infos, 1):
            # Hapus pengeditan status_msg per video individu di sini
            # current_video_status_text = (
            #     f"📥 **[{idx}/{total_videos_in_url}] Mengunduh:** `{video_info['filename']}`\n"
            #     f"📊 **Ukuran:** {video_info.get('size', 'Unknown')}\n"
            #     f"⏱️ **Durasi:** {video_info.get('duration', 'Unknown')}\n\n"
            #     f"Progres video ini: **{idx}/{total_videos_in_url}**"
            # )
            # await status_msg.edit(current_video_status_text, buttons=create_back_keyboard())

            try:
                filepath = await download_video_with_retry(video_info['video_url'], video_info['filename'])
                filepaths.append(filepath)
            except DownloadError as e:
                log.error(f"Download gagal untuk {video_info['filename']}: {str(e)}")
                # Hapus pengeditan status_msg pada kegagalan unduhan per video
                # await status_msg.edit(f"❌ **Gagal Unduh:** `{video_info['filename']}`\n\n{str(e)}", buttons=create_back_keyboard())
                continue # Lanjutkan ke video berikutnya jika ada

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            video_title = os.path.splitext(os.path.basename(filepath))[0]
            caption = (
                f"🎬 **{video_title}**\n\n"
                f"💾 **Ukuran File:** {file_size_mb:.1f} MB\n"
                f"⏱️ **Durasi:** {video_info.get('duration', 'Unknown')}\n"
                f"📊 **Ukuran Asli:** {video_info.get('size', 'Unknown')}\n\n"
                f"📁 **Nama file asli:** `{video_info.get('original_filename', 'N/A')}`\n\n"
                f"🤖 **Diunduh dengan VideoBot**"
            )

            try:
                await upload_with_retry(client, chat_id, filepath, caption)
                successful_uploads_for_url += 1
            except UploadError as e:
                log.error(f"Unggahan gagal untuk {video_info['filename']}: {str(e)}")
                # Hapus pengeditan status_msg pada kegagalan unggahan per video
                # await status_msg.edit(f"❌ **Gagal Unggah:** `{video_info['filename']}`\n\n{str(e)}", buttons=create_back_keyboard())
                continue
        
        # Mengembalikan hasil boolean untuk digunakan oleh message_handler.
        # Tidak ada edit status per URL akhir di sini.
        return successful_uploads_for_url > 0

    except DownloadError as e:
        log.error(f"❌ Pengambilan info video awal gagal untuk {url}: {str(e)}")
        # Ini menunjukkan kegagalan langsung untuk mengurai URL itu sendiri. TETAPKAN INI.
        await status_msg.edit(f"❌ **Info video awal gagal:** {str(e)}", buttons=create_back_keyboard())
        return False
    except Exception as e:
        log.error(f"❌ Terjadi error tak terduga dalam process_video_download untuk {url}: {str(e)}")
        # Untuk error tak terduga yang spesifik untuk URL ini. TETAPKAN INI.
        await status_msg.edit(f"❌ **Error tak terduga:** {str(e)}", buttons=create_back_keyboard())
        return False
    finally:
        for filepath in filepaths:
            await safe_cleanup(filepath)


def register_handlers(client: TelegramClient):
    @client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        """Handler untuk perintah /start"""
        welcome_text = (
            f"🎬 **Selamat Datang di Enhanced Video Bot!**\n\n"
            f"👋 Halo {event.sender.first_name}!\n\n"
            f"🚀 **Yang bisa saya lakukan:**\n"
            f"• 📥 Mengunduh video dari berbagai platform\n"
            f"• 🔧 Memperbaiki nama file yang rusak secara otomatis\n"
            f"• 📱 Antarmuka yang ramah pengguna\n"
            f"• ⚡ Unduhan cepat & handal\n\n"
            f"**Pilih opsi di bawah untuk memulai:**"
        )
        await event.reply(welcome_text, buttons=create_main_keyboard())

    @client.on(events.CallbackQuery)
    async def callback_handler(event):
        """Handler untuk semua callback query dari tombol inline"""
        data = event.data.decode('utf-8')
        chat_id = event.chat_id
        user_id = event.sender_id

        if data == "start":
            welcome_text = (
                f"🎬 **Selamat Datang di Enhanced Video Bot!**\n\n"
                f"👋 Halo {event.sender.first_name}!\n\n"
                f"🚀 **Yang bisa saya lakukan:**\n"
                f"• 📥 Mengunduh video dari berbagai platform\n"
                f"• 🔧 Memperbaiki nama file yang rusak secara otomatis\n"
                f"• 📱 Antarmuka yang ramah pengguna\n"
                f"• ⚡ Unduhan cepat & handal\n\n"
                f"**Pilih opsi di bawah untuk memulai:**"
            )
            await event.edit(welcome_text, buttons=create_main_keyboard())
            return

        if data == "main_menu":
            await event.edit(
                f"🎬 **Menu Utama Video Bot**\n\n"
                f"Selamat datang kembali! Pilih apa yang ingin Anda lakukan:",
                buttons=create_main_keyboard()
            )
        
        elif data == "download_video":
            await event.edit(
                f"📥 **Unduh Video**\n\n"
                f"Pilih bagaimana Anda ingin menyediakan URL video:",
                buttons=create_download_keyboard()
            )
        
        elif data == "paste_url":
            USER_STATES[user_id] = "waiting_for_url"
            await event.edit(
                f"🔗 **Tempel URL Video**\n\n"
                f"Silakan kirimkan saya URL video yang ingin Anda unduh.\n"
                f"**Anda bisa mengirimkan beberapa URL (satu per baris).**\n\n"
                f"**Platform yang didukung:**\n"
                f"• YouTube, TikTok, Instagram\n"
                f"• Facebook, Twitter, Reddit\n"
                f"• Dan banyak lagi!\n\n"
                f"Cukup tempel URL-nya dan saya akan mengurus sisanya! 🚀",
                buttons=create_back_keyboard()
            )
        
        elif data == "url_clipboard":
            await event.answer("⚠️ Fitur papan klip akan segera hadir!", alert=True)
        
        elif data == "bot_status":
            try:
                # Pastikan DOWNLOAD_FOLDER ada sebelum mencantumkan isinya
                if not os.path.exists(DOWNLOAD_FOLDER):
                    os.makedirs(DOWNLOAD_FOLDER)

                file_count = len([f for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))])
                
                total_size = 0
                for filename in os.listdir(DOWNLOAD_FOLDER):
                    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                
                status_text = (
                    f"📊 **Status Bot**\n\n"
                    f"🟢 **Status:** Online & Siap\n"
                    f"📁 **File sementara:** {file_count} file\n"
                    f"💾 **Penyimpanan terpakai:** {total_size/1024/1024:.1f} MB\n"
                    f"⚙️ **Maks percobaan ulang:** {MAX_RETRIES}\n"
                    f"⏱️ **Penundaan percobaan ulang:** {RETRY_DELAY}s\n"
                    f"📏 **Maks ukuran file:** {MAX_FILE_SIZE/1024/1024:.0f} MB\n\n"
                    f"🔧 **Performa:** Optimal"
                )
                
                await event.edit(status_text, buttons=create_back_keyboard())
            except Exception as e:
                await event.edit(f"❌ **Gagal Cek Status**\n\n{str(e)}", buttons=create_back_keyboard())
        
        elif data == "cleanup":
            try:
                files_removed = 0
                if os.path.exists(DOWNLOAD_FOLDER):
                    for filename in os.listdir(DOWNLOAD_FOLDER):
                        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_removed += 1
                
                await event.edit(
                    f"🗑️ **Pembersihan Selesai**\n\n"
                    f"✅ **{files_removed} file** berhasil dihapus!\n"
                    f"💾 **Penyimpanan dikosongkan**\n\n"
                    f"Bot Anda sekarang berjalan bersih! 🚀",
                    buttons=create_back_keyboard()
                )
                log.info(f"Pembersihan manual: {files_removed} file dihapus")
            except Exception as e:
                await event.edit(f"❌ **Pembersihan Gagal**\n\n{str(e)}", buttons=create_back_keyboard())
        
        elif data == "help":
            help_text = (
                f"ℹ️ **Bantuan & Panduan**\n\n"
                f"**🚀 Cara menggunakan:**\n"
                f"1️⃣ Klik **Unduh Video**\n"
                f"2️⃣ Pilih **Tempel URL**\n"
                f"3️⃣ Kirim URL video Anda (bisa banyak, satu per baris)\n"
                f"4️⃣ Tunggu unduhan & unggahan\n"
                f"5️⃣ Nikmati video Anda! 🎉\n\n"
                f"**🔧 Fitur:**\n"
                f"• Perbaikan nama file otomatis\n"
                f"• Pelacakan progres\n"
                f"• Pemulihan error\n"
                f"• Mendukung berbagai format\n\n"
                f"**💡 Tips:**\n"
                f"• Gunakan URL asli (bukan yang dipersingkat)\n"
                f"• Periksa batas ukuran file\n"
                f"• Bersabar dengan file besar\n\n"
                f"**⚠️ Batasan:**\n"
                f"• Maks ukuran file: {MAX_FILE_SIZE/1024/1024:.0f}MB\n"
                f"• Maks percobaan ulang: {MAX_RETRIES} kali"
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
                f"• Maks Percobaan Ulang: **{MAX_RETRIES}**\n"
                f"• Penundaan Percobaan Ulang: **{RETRY_DELAY}s**\n"
                f"• Ukuran Chunk: **{CHUNK_SIZE/1024}KB**\n\n"
                f"Pengaturan ini memastikan unduhan yang andal bahkan dengan koneksi yang tidak stabil.",
                buttons=create_back_keyboard()
            )
        
        elif data == "file_settings":
            await event.edit(
                f"📁 **Pengaturan File**\n\n"
                f"**Konfigurasi Saat Ini:**\n"
                f"• Maks Ukuran File: **{MAX_FILE_SIZE/1024/1024:.0f}MB**\n"
                f"• Folder Unduhan: **{DOWNLOAD_FOLDER}**\n"
                f"• Pembersihan Otomatis: **Diaktifkan**\n"
                f"• Perbaikan Nama File: **Diaktifkan**\n\n"
                f"File secara otomatis dibersihkan setelah diunggah untuk menghemat ruang.",
                buttons=create_back_keyboard()
            )

    @client.on(events.NewMessage)
    async def message_handler(event):
        """Handler untuk pesan reguler (URL saat dalam status menunggu)"""
        user_id = event.sender_id
        text = event.text
        chat_id = event.chat_id # Mendapatkan chat_id dari event
        
        # Lewati jika itu adalah perintah
        if text.startswith('/'):
            return 
        
        # Periksa apakah pengguna sedang menunggu URL
        if USER_STATES.get(user_id) == "waiting_for_url":
            # Reset status pengguna
            USER_STATES.pop(user_id, None)
            
            # Pisahkan teks input menjadi baris-baris, saring baris kosong, dan hilangkan spasi
            urls_from_input = [line.strip() for line in text.split('\n') if line.strip()]
            
            if not urls_from_input:
                await event.reply(
                    f"❌ **Input Tidak Valid**\n\n"
                    f"Harap berikan setidaknya satu URL video.",
                    buttons=create_main_keyboard()
                )
                return

            valid_urls = []
            for url in urls_from_input:
                # Validasi URL dasar menggunakan regex
                # Ini adalah validasi yang sangat dasar, mungkin perlu diperluas
                if re.match(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', url):
                    valid_urls.append(url)
                else:
                    log.warning(f"URL tidak valid dilewati: {url}")
            
            if not valid_urls:
                await event.reply(
                    f"❌ **Tidak Ditemukan URL Valid**\n\n"
                    f"Semua URL yang diberikan tidak valid. Pastikan itu adalah tautan video yang benar.",
                    buttons=create_main_keyboard()
                )
                return
            
            # Kirim pesan awal yang menunjukkan bahwa proses multi-URL dimulai
            initial_reply = await event.reply(f"🚀 **Memulai proses unduhan untuk {len(valid_urls)} URL...**")
            
            total_processed_urls = len(valid_urls)
            successful_urls_count = 0
            failed_urls_list = [] # List untuk menyimpan URL yang gagal

            # Proses setiap URL satu per satu
            for i, url_to_process in enumerate(valid_urls):
                # PERBAIKAN: Menghapus tautan GitHub yang hardcode dari status_msg_text
                status_msg_text = (
                   
                    f"🔍 Mengambil informasi video..."
                )
                
                # Kirim pesan status baru untuk setiap URL dalam daftar
                current_status_message = await client.send_message(
                    chat_id,
                    status_msg_text,
                    buttons=create_back_keyboard()
                )
                
                # Panggil process_video_download untuk setiap URL
                success = await process_video_download(client, event.chat_id, url_to_process, current_status_message)
                if success:
                    successful_urls_count += 1
                else:
                    failed_urls_list.append(url_to_process) # Tambahkan URL yang gagal ke daftar
            
            # Kirim pesan ringkasan akhir setelah semua URL diproses
            final_summary = (
                f"✅ **Proses Selesai!**\n\n"
                f"📊 **Ringkasan:**\n"
                f"- Total URL yang diproses: **{total_processed_urls}**\n"
                f"- Berhasil diunduh & diunggah: **{successful_urls_count}**\n"
                f"- Gagal: **{total_processed_urls - successful_urls_count}**\n"
            )

            if failed_urls_list:
                final_summary += "\n❌ **URL yang Gagal:**\n"
                for failed_url in failed_urls_list:
                    final_summary += f"- `{failed_url}`\n"

            final_summary += "\nKlik tombol di bawah untuk tindakan selanjutnya."

            await client.send_message(
                chat_id,
                final_summary,
                buttons=create_main_keyboard()
            )

    # Dukungan perintah lama
    @client.on(events.NewMessage(pattern=r'^/getvideo (.+)'))
    async def legacy_handler(event):
        """Handler perintah lama untuk kompatibilitas mundur"""
        url = event.pattern_match.group(1).strip()
        
        status_msg = await event.reply(
            f"🔍 **Memproses Perintah Lama**\n\n"
            f"🔗 **URL:** `{url[:50]}{'...' if len(url) > 50 else ''}`\n\n"
            f"Mohon tunggu...",
            buttons=create_back_keyboard()
        )
        
        # Teruskan klien ke process_video_download
        await process_video_download(client, event.chat_id, url, status_msg)