#!/usr/bin/env python3
"""
Standalone scanner service.
Runs independently from API workers to avoid lock contention and timeouts.
"""
import logging
import os
import time
from app.scanner import scan
from app.db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
    scan_interval = int(os.getenv("SCAN_INTERVAL", 3600))
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
    
    # --- PERIODIC SCANNING ---
    if scan_interval == 0:
        logger.info("SCAN_INTERVAL is 0. Periodic scanning disabled. Exiting.")
        return
    
    logger.info(f"Starting periodic scan loop (interval: {scan_interval}s)...")
    while True:
        time.sleep(scan_interval)
        try:
            logger.info("Starting periodic scan (no limit)...")
            scan(limit=None)
            logger.info("Periodic scan completed.")
        except Exception as e:
            logger.error(f"Error during periodic scan: {e}", exc_info=True)

if __name__ == "__main__":
    main()
