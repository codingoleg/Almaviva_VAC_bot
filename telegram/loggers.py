import logging

CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10
NOTSET = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def log(user_id: int, message: str = None, level: int = DEBUG):
    """
    Creates custom logger with user_id, message (optional), level.
    Logging filename is the same as user id.
    """

    # Remove previous FileHandler
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.handlers.remove(handler)

    # Initialize and add new FileHandler
    file_handler = logging.FileHandler(
        filename=f'./telegram/logs/{str(user_id)}.log', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Set level
    if level == DEBUG:
        logger.debug(message)
    elif level == INFO:
        logger.info(message)
    elif level == WARNING:
        logger.warning(message)
    elif level == ERROR:
        logger.error(message, exc_info=True)
    elif level == CRITICAL:
        logger.critical(message, exc_info=True)
