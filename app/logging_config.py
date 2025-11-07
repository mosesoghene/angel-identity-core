import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

# --- Log Configuration ---
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def setup_logging():
    """Configures logging for the application."""
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # --- File Handler ---
    # Rotates log files daily.
    log_file = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # --- Console Handler ---
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG) # Or your preferred level

    # --- Root Logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Set to the lowest level
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # --- Specific Loggers ---
    # Quieten overly verbose libraries if needed.
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("✓ Logging configured successfully.")

setup_logging()