import logging
import os
from datetime import datetime

def setup_logger(name="ETL_pipeline"):
    log_dir = "../logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"etl_{datetime.now().strftime('%Y-%m-%d')}.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_format = logging.Formatter('%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger