#!/usr/bin/env python3
"""
Standalone scanner service.
Runs independently from API workers to avoid lock contention and timeouts.
"""
import logging
import os
import time
from app.scanner import scan, precompute_missing_thumbnails, GALLERY_PATH
from app.watcher import start_watcher
from app.db import init_db

import logging
from logging.handlers import RotatingFileHandler

# Configure logging
log_dir = "/app/data/logs"
os.makedirs(log_dir, exist_ok=True)

log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# File handler
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "scanner.log"),
    maxBytes=10*1024*1024, # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

# Paths
DATA_DIR = "/app/data"
INITIAL_SCAN_FLAG_PATH = os.path.join(DATA_DIR, ".initial_scan_complete")

def main():
    """Main scanner service loop."""
    logger.info("Scanner service starting...")
    
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Get configuration from environment
    # Default to 6 hours (21600s) for safety scan if not specified
    scan_interval = int(os.getenv("SCAN_INTERVAL", 21600))
    initial_scan_max = int(os.getenv("INITIAL_SCAN_MAX_MEDIA", 5000))
    
    # --- INITIAL SCAN ---
    if not os.path.exists(INITIAL_SCAN_FLAG_PATH):
        logger.info(f"Running initial scan (limited to {initial_scan_max} files)...")
        try:
            scan(limit=initial_scan_max)
            # Mark initial scan as complete
            with open(INITIAL_SCAN_FLAG_PATH, 'w') as f:
                f.write('done')
            logger.info("Initial scan completed successfully.")
        except Exception as e:
            logger.error(f"Error during initial scan: {e}", exc_info=True)
    else:
        logger.info("Initial scan already completed (flag file exists).")
    
    # --- START WATCHER ---
    logger.info("Initializing real-time file watcher...")
    observer, queue = start_watcher(GALLERY_PATH)
    
    # --- PERIODIC SAFETY SCANNING & THUMBNAIL PRECOMPUTATION ---
    logger.info(f"Starting main service loop (Safety scan interval: {scan_interval}s)...")
    last_thumb_id = 0  # Track pagination cursor
    try:
        while True:
            # Utilize the scan_interval window to precompute thumbnails
            start_wait = time.time()
            consecutive_batches = 0  # Track how many batches processed in a row
            
            while time.time() - start_wait < scan_interval:
                try:
                    # Adaptive batch size: start large (200) for catch-up, then drop to 50 for responsiveness
                    adaptive_batch = 200 if consecutive_batches < 3 else 50
                    
                    processed_any, last_thumb_id = precompute_missing_thumbnails(
                        batch_size=adaptive_batch,
                        last_processed_id=last_thumb_id
                    )
                    
                    if processed_any:
                        consecutive_batches += 1
                        # Very small sleep to yield CPU between batches
                        time.sleep(1)
                        continue
                    else:
                        # No thumbnails to process in this cycle
                        # If we've completed a full pagination cycle (last_thumb_id reset to 0),
                        # we're fully caught up - break out to trigger periodic scan
                        if last_thumb_id == 0 and consecutive_batches == 0:
                            logger.info("Thumbnail precomputation caught up. Breaking to periodic scan.")
                            break
                        
                        consecutive_batches = 0
                        # Sleep for a short interval before checking again
                        remaining = scan_interval - (time.time() - start_wait)
                        if remaining > 0:
                            time.sleep(min(remaining, 10))  # Check every 10s instead of 60s
                except Exception as e:
                    logger.error(f"Error during thumbnail precomputation: {e}", exc_info=True)
                    consecutive_batches = 0
                    time.sleep(10) # Prevent tight error loops
                    
            try:
                logger.info("Starting periodic safety scan (no limit)...")
                scan(limit=None)
                logger.info("Periodic safety scan completed.")
            except Exception as e:
                logger.error(f"Error during periodic scan: {e}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Scanner service stopping...")
        observer.stop()
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        observer.stop()
    
    observer.join()
    queue.stop()

if __name__ == "__main__":
    main()
