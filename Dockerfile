# Gunakan base image Python resmi
# Alpine lebih ringan, tapi kadang ada isu dependensi binary, jadi kita pakai Debian slim
FROM python:3.10-slim-buster

# Atur direktori kerja di dalam kontainer
WORKDIR /app

# Nonaktifkan buffering output Python, sehingga log segera terlihat di konsol
ENV PYTHONUNBUFFERED 1

# Salin file requirements.txt dan instal dependensi
# Gunakan --no-cache-dir untuk menghemat ruang disk pada image
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode aplikasi Anda ke dalam kontainer
# Pastikan ini dilakukan setelah instalasi dependensi, untuk memanfaatkan Docker layer caching
COPY . .

# Buat direktori 'downloads' jika belum ada, dan berikan izin yang sesuai
# Ini penting agar bot bisa menyimpan file yang diunduh
RUN mkdir -p downloads && chmod -R 777 downloads

# Komando untuk menjalankan aplikasi saat kontainer dimulai
# Menggunakan 'python' langsung agar sinyal SIGTERM dapat ditangani dengan baik
CMD ["python", "main_runner.py"]