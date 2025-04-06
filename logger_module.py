from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    format="<level>{time:YYYY-MM-DD HH:mm:ss} | {level} | {file} | {message}</level>",
    level="INFO",
    colorize=True,
    enqueue=True,
)

logger.add(
    "debug_logs.log",  # or use Path if needed
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
    level="DEBUG",
    rotation="10 MB",  # optional: rotate file after it reaches 10 MB
    compression="zip",  # optional: compress rotated logs
    enqueue=True,
)
