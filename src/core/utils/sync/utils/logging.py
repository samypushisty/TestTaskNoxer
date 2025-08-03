import logging
from datetime import datetime


def setup_logger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    """Настройка логгера без дублирования обработчиков"""
    logger = logging.getLogger(name)

    # Очищаем существующие обработчики, чтобы избежать дублирования
    if logger.handlers:
        logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(file_handler)

    return logger


def log_sync_start(logger: logging.Logger, on_main: bool):
    """Логирование начала синхронизации"""
    logger.info(f"Starting data synchronization (on_main={on_main}) at {datetime.now()}")


def log_sync_complete(logger: logging.Logger, report: str):
    """Логирование завершения синхронизации"""
    logger.info(f"Data synchronization completed. Report:\n{report}")