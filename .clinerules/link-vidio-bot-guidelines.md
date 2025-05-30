## Ringkasan singkat
- jika ada error maka liat lah refernsi script ddanfungsionalitas dari pedoman_bot.py pedoman_poophd.py
- Pedoman khusus proyek untuk mengembangkan Link_vidio_bot downloader video Telegram
- Fokus pada arsitektur modular dengan pemisahan jelas antara logika bot, fungsionalitas inti, dan helper
- Penekanan pada pola async/await untuk operasi I/O dan interaksi UI keyboard inline
- Kewajiban menggunakan bahasa Indonesia untuk teks yang ditampilkan ke pengguna

## Gaya komunikasi
- Prioritaskan presisi teknis daripada gaya percakapan
- Hindari pertanyaan berulang ketika konteks sudah jelas dari struktur proyek
- Selalu jelaskan saran kode terkait arsitektur yang ada
- Gunakan diagram mermaid untuk penjelasan alur kerja kompleks
- Sertakan contoh konkret saat menjelaskan perubahan kode

## Alur kerja pengembangan
- Selalu analisis struktur proyek terlebih dahulu menggunakan list_files dan search_files
- Ikuti tanggung jawab modul yang sudah ada secara ketat:
  - bot/ untuk handler Telegram dan UI
  - core/ untuk logika pemrosesan video
  - utils/ untuk helper reusable
- Verifikasi ketersediaan fungsi reusable sebelum implementasi baru
- Gunakan replace_in_file untuk edit terarah daripada overwrite seluruh isi file
- Pastikan setiap perubahan kode menjaga konsistensi dengan:
  - Pola async/await di seluruh operasi I/O
  - Penanganan error yang informatif
  - Struktur direktori yang sudah ada

## Praktik terbaik pemrograman
- Wajib menggunakan async/await untuk semua operasi I/O
- Harus ada blok try-except untuk operasi jaringan/file
- Gunakan bot.config.log untuk logging daripada print()
- Variabel lingkungan harus diakses melalui modul bot.config
- Semua string yang ditampilkan ke pengguna harus dalam bahasa Indonesia
- Kode harus mengikuti pedoman berikut:
  - Impor modul menggunakan format relatif (from ..core.downloader import ...)
  - Fungsi async harus selalu diakhiri dengan async
  - Penamaan variabel menggunakan snake_case dengan deskripsi jelas
  - Komentar kode harus menjelaskan konteks teknis, bukan hanya menerjemahkan kode ke bahasa alami

## Konteks proyek
- Direktori inti:
  - bot/ (handlers, keyboards, config)
    - handlers.py: logika respons terhadap perintah Telegram
    - keyboards.py: definisi UI keyboard inline
    - config.py: pengelolaan token dan konfigurasi global
  - core/ (downloader, uploader, scraper)
    - downloader.py: manajemen proses pengunduhan video
    - uploader.py: logika pengunggahan ke Telegram
    - poop_scraper.py: ekstraksi metadata dari PoopHD.com
  - utils/ (helper umum)
    - helpers.py: fungsi sanitasi string dan pembersihan file

## Pedoman lain
- Jangan pernah hardcode kredensial atau API key
  - Gunakan modul bot.config untuk akses variabel lingkungan
- Jaga konsistensi pola impor di seluruh modul:
  - Impor relatif untuk modul internal (from ..core.downloader import ...)
  - Impor absolut untuk dependensi eksternal (import asyncio)
- Selalu sertakan konteks penanganan error dalam penjelasan kode:
  - Contoh penanganan error untuk timeout jaringan:
    try:
      response = await fetch(...)
    except TimeoutError:
      bot.config.log.error("Network timeout saat mengunduh video")
- Gunakan warna kontras tinggi dalam diagram mermaid untuk keterbacaan
- Jalur file harus menggunakan slash (/) terlepas dari OS
- Hindari penambahan fitur baru di luar ruang lingkup proyek:
  - Tidak menambahkan fitur download dari sumber selain PoopHD.com
  - Tidak mengubah UI menjadi teks biasa tanpa keyboard inline
