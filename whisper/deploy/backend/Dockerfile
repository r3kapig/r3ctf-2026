FROM python:3.10-slim

WORKDIR /app

# Install deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Data volume mount point
VOLUME ["/app/data"]

ENV WHISPER_DATA_DIR=/app/data
ENV WHISPER_CTF_MODE=1
ENV WHISPER_HOST=0.0.0.0
ENV WHISPER_PORT=8000

EXPOSE 8000

CMD ["python", "main.py"]
