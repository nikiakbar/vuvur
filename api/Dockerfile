FROM python:3.11-slim

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

# Make the new startup script executable
RUN chmod +x run.sh

EXPOSE 5000

# Set the command to our new script
CMD ["./run.sh"]