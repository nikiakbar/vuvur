# Vuvur Media Gallery

> **Note:** This README file was generated entirely by an AI assistant based on the project's source code.

Vuvur is a self-hosted media gallery designed for browsing and managing large collections of images and videos. It consists of a Python-based backend API, a modern React web interface, and a native Android application.

The backend automatically scans designated directories, extracts metadata (including EXIF data from AI-generated images), and serves the content to the clients. The frontends provide a responsive, user-friendly interface for infinite scrolling, searching, and viewing media.

---
## Feature Checklist

### Core Backend (API)
- [x] Automatic media scanning of specified directories
- [x] Periodic background scanning to find new files
- [x] SQLite database for storing media metadata
- [x] Efficient full-text search using FTS5
- [x] Dynamic thumbnail and preview generation (images & videos)
- [x] High-performance media streaming with support for byte-range requests
- [x] Endpoints for random media browsing
- [x] "Liking" functionality (moves files to a `liked` directory)
- [x] Optional user authentication system (can be enabled/disabled)
- [x] API for managing application settings
- [x] Dockerized for easy deployment

### Web Frontend (Portal)
- [x] Masonry-style infinite scroll gallery
- [x] Fast, responsive media viewer with zoom and pan
- [x] Support for both image and video playback
- [x] Light and Dark mode themes
- [x] Sorting and filtering options in the gallery view
- [x] Page for viewing random media
- [x] Settings page to trigger cache cleanup and re-scans
- [x] Dynamic configuration via environment variables at runtime

### Android App
- [x] Native media gallery with staggered grid layout
- [x] Infinite scrolling with pagination
- [x] Fullscreen media viewer with zoom and pan for images
- [x] Native video playback
- [x] Random media scroller
- [x] Settings screen to switch API endpoints and clear cache
- [ ] Offline caching or viewing capabilities
- [ ] EXIF data display in the viewer
- [ ] "Liking" and deleting functionality from the viewer

---
## Core Technologies

| Component | Technology / Library |
| :--- | :--- |
| **Backend API** | Python, Flask, Gunicorn, SQLite, Pillow, ffmpeg |
| **Web Frontend** | React, Vite, Nginx, JavaScript |
| **Android App** | Kotlin, Jetpack Compose, Retrofit, Coil, Media3 ExoPlayer |
| **Deployment** | Docker, Docker Compose |

---
## Getting Started

The Vuvur application is designed to be run using Docker and Docker Compose.

### 1. Prerequisites
* Docker
* Docker Compose

### 2. Configuration

Create a `docker-compose.yml` file in the root of the project. You can use the provided `compose.yaml` as a starting point.

You must configure the `volumes` section to map the directories on your host machine containing your media files to the paths expected by the container (`/mnt/gallery/...`).

### 3. Environment Variables

You can configure the application's behavior by setting environment variables in your `docker-compose.yml` file.

**API Service (`api`):**
* `SCAN_INTERVAL`: How often (in seconds) the background scanner should run. Set to `0` to disable. (Default: `3600`)
* `SECRET_KEY`: A secret key for Flask sessions. (Default: `dev`)
* `ENABLE_LOGIN`: Set to `true` to enable user authentication. (Default: `false`)

**Portal Service (`portal`):**
* `VITE_ZOOM_LEVEL`: The default zoom level in the media viewer. (e.g., `2.5`)
* `VITE_GALLERY_BATCH_SIZE`: The number of images to load per page in the gallery. (e.g., `20`)
* `VITE_RANDOM_PRELOAD_COUNT`: The number of images to preload on the random scroller. (e.g., `3`)

### 4. Running the Application

Once your `docker-compose.yml` is configured, you can start the application with the following command:

```bash
docker-compose up --build