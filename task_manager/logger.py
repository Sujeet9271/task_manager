import logging
from logging.handlers import TimedRotatingFileHandler

from task_manager import settings

logging.basicConfig(format='%(levelname)s - %(asctime)s, %(pathname)s:%(lineno)d , message: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if settings.DEBUG:
    logger.setLevel(logging.DEBUG)

# # Create a timed rotating file handler that rotates the log every day and keeps 7 backups (one week)
# file_handler = TimedRotatingFileHandler('log_websocket.log', when='D', interval=1, backupCount=7)
# file_handler.setLevel(logging.INFO)
# logger.addHandler(file_handler)