import os
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from app.scanner import process_single_file, delete_single_file, GALLERY_PATH, RECYCLEBIN_PATH

logger = logging.getLogger(__name__)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".wma", ".aac"}

class MediaEventHandler(FileSystemEventHandler):
    def __init__(self, queue):
        self.queue = queue

    def on_created(self, event):
        if not event.is_directory:
            self._handle_event(event.src_path, "upsert")

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_event(event.src_path, "upsert")

    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_event(event.src_path, "delete")

    def on_moved(self, event):
        if not event.is_directory:
            self._handle_event(event.src_path, "delete")
            self._handle_event(event.dest_path, "upsert")

    def _handle_event(self, path, action):
        if RECYCLEBIN_PATH in path:
            return
            
        ext = os.path.splitext(path)[1].lower()
        if ext in VALID_EXTENSIONS:
            self.queue.put(path, action)

class DebouncedEventQueue:
    def __init__(self, debounce_seconds=2.0):
        self.debounce_seconds = debounce_seconds
        self.pending_actions = {} # path -> (action, timestamp)
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def put(self, path, action):
        with self.lock:
            # If we already have a delete pending and get an upsert, or vice versa, 
            # we just take the latest action and reset the timer.
            self.pending_actions[path] = (action, time.time())
            # logger.debug(f"Queued {action} for {path}")

    def _worker(self):
        while not self._stop_event.is_set():
            to_process = []
            with self.lock:
                now = time.time()
                for path, (action, timestamp) in list(self.pending_actions.items()):
                    if now - timestamp >= self.debounce_seconds:
                        to_process.append((path, action))
                        del self.pending_actions[path]
            
            for path, action in to_process:
                try:
                    if action == "upsert":
                        process_single_file(path)
                    elif action == "delete":
                        delete_single_file(path)
                except Exception as e:
                    logger.error(f"Error processing debounced event for {path}: {e}")

            time.sleep(0.5)

    def stop(self):
        self._stop_event.set()
        self._worker_thread.join()

def start_watcher(path):
    """Starts the watchdog observer."""
    logger.info(f"Starting watchdog observer for {path}...")
    
    queue = DebouncedEventQueue()
    event_handler = MediaEventHandler(queue)
    
    # Check if we should use PollingObserver (useful for network mounts)
    use_polling = os.getenv("WATCHDOG_POLLING", "0") == "1"
    
    if use_polling:
        logger.info("Using PollingObserver (WATCHDOG_POLLING=1)")
        observer = PollingObserver()
    else:
        logger.info("Using native Observer")
        observer = Observer()
        
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    
    return observer, queue
