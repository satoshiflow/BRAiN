import logging
import sys
from pythonjsonlogger import jsonlogger

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(LOG_FORMAT)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence overly noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
