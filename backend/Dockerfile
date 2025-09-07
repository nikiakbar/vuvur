# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install ffmpeg and add sqlite3 CLI tool
RUN apt-get update && apt-get install -y ffmpeg sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]