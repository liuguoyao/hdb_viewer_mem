import os
import logging
import threading
import logging.handlers

initLock = threading.Lock()
rootLoggerInitialized = False

log_format = "%(asctime)s %(filename)s:%(lineno)d [%(levelname)s] %(message)s"
level = logging.INFO
file_log = r"./log/log_msg.txt"  # File name
console_log = True


def init_handler(handler):
    """
    set format for handler
    """
    handler.setFormatter(logging.Formatter(log_format))


def init_logger(logger):
    logger.setLevel(level)
    if file_log is not None:
        file_dir = os.path.dirname(os.path.abspath(file_log))
        os.makedirs(file_dir, exist_ok=True)
        file_handler = logging.handlers.TimedRotatingFileHandler(file_log, when="D", interval=1, backupCount=30)
        init_handler(file_handler)
        logger.addHandler(file_handler)

    if console_log:
        console_handler = logging.StreamHandler()
        init_handler(console_handler)
        logger.addHandler(console_handler)


def initialize():
    """
    initialize the root logger for the first time
    """
    global rootLoggerInitialized
    with initLock:
        if not rootLoggerInitialized:
            init_logger(logging.getLogger())
            rootLoggerInitialized = True

def get_logger(name=None):
    initialize()
    return logging.getLogger(name)
