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
