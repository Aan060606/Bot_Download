# Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh isi proyek. Dengan adanya volumes di docker-compose.yml,
# perubahan pada script tidak memerlukan rebuild image ini.
COPY . .

RUN mkdir -p downloads

CMD ["python", "main_runner.py"]