from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    format="<level>{time:YYYY-MM-DD HH:mm:ss} | {level} | {file} | {message}</level>",
    level="TRACE",
    colorize=True,
    enqueue=True,
)
