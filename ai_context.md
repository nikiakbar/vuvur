# Vuvur: AI Context & Development Guidelines

This document serves as the primary context for AI assistants working on the Vuvur project. It outlines the project's goals, current implementation details, and core requirements.

## 🚀 Core Objectives

1.  **Masonry Layout**: A performant, aesthetically pleasing masonry grid is a mandatory requirement for the media gallery.
2.  **Google Photos Experience**: The application should strive to mimic the UX and performance of Google Photos (smooth scrolling, fast zooming, intuitive navigation).
3.  **No Upload (Current Phase)**: The current focus is on managing and viewing *existing* media. Upload functionality is NOT required at this stage.
4.  **Existing Media Focus**: The app must efficiently read and display media from specified local directories.
5.  **Instant Scanning**: The app should "scan on the go." Users should be able to start browsing media as soon as the app starts, without waiting for a full initial scan to complete. Scanning and streaming should be as fast as possible.
6.  **Modern Stack**: Use the latest stable versions of libraries and frameworks to ensure performance and maintainability.

## 🛠 Tech Stack

### Backend (API)
- **Language**: Python
- **Framework**: Flask
- **Database**: SQLite (using FTS5 for search)
- **Processing**:
    - **Pillow**: Image processing and metadata extraction.
    - **piexif**: Robust EXIF metadata extraction for JPEG/WebP.
    - **ffmpeg/ffprobe**: Video metadata and thumbnail generation.
- **Concurrency**: Background scanning implemented with Python `threading` and `concurrent.futures.ThreadPoolExecutor` for parallel processing of file stats and metadata.

### Frontend (Portal)
- **Framework**: React (Vite-based)
- **State Management**: Standard React hooks/context.
- **Gallery/Layout**:
    - `react-masonry-css`: Current masonry implementation.
    - `@tanstack/react-virtual`: Used for efficient rendering of large lists via virtualization.
- **Routing**: `react-router-dom`
- **Styling**: Vanilla CSS (Modern CSS features prioritized).

## 📂 Project Structure

- `/api`: Python Flask backend.
    - `/app`: Core logic (scanning, database, API blueprints).
- `/portal`: React frontend.
    - `/src`: Frontend components and logic.
- `/docker-compose.yaml`: Deployment configuration.

## 📝 Key Implementation Details

- **Scanning Logic**: Found in `api/app/scanner.py`. It uses `os.walk` for discovery and parallelizes metadata extraction.
- **Streaming**: Supports byte-range requests for efficient video playback.
- **Thumbnails**: Dynamically generated and cached.

## ⚠️ Development Constraints

- **DO NOT** implement file upload features.
- **DO** ensure any layout changes maintain masonry behavior.
- **DO** prioritize performance, especially for the initial scan experience.
- **DO** use modern CSS and avoid heavy third-party UI libraries unless necessary.
