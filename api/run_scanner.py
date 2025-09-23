import logging
import os
from app.scanner import scan
from app.db import init_db

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Define the path for the flag file and data directory
DATA_DIR = "/app/data"
INITIAL_SCAN_FLAG_PATH = os.path.join(DATA_DIR, ".initial_scan_complete")

if __name__ == '__main__':

    os.makedirs(DATA_DIR, exist_ok=True)

    logging.info("Initializing database from script...")
    init_db()
    logging.info("Starting library scan from script...")
    scan()
    # Create the flag file to signal that the initial scan is done
    with open(INITIAL_SCAN_FLAG_PATH, 'w') as f:
        f.write('done')
    logging.info("Library scan script finished and completion flag created.")