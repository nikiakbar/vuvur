FROM python:3.11-slim

# Install ffmpeg and add sqlite3 CLI tool
RUN apt-get update && apt-get install -y \
    ffmpeg \
    sqlite3 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "__init__:create_app()"]