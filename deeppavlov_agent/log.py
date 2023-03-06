import logging
import logging.handlers
from queue import Queue
from typing import Iterator
from contextlib import contextmanager

from .settings import (
    LOG_FILE,
    LOG_LEVEL,
    LogDest,
    LOG_DEST,
    LOG_FILE_SIZE,
    LOG_BACKUP_COUNT,
)


@contextmanager
def setup() -> Iterator[None]:
    queue: Queue[str] = Queue(-1)
    formatter = logging.Formatter(
        fmt="[%(asctime)s.%(msecs)d] %(levelname)s [%(module)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    dp_agent = logging.getLogger("deeppavlov_agent")
    dp_agent.propagate = False
    dp_agent.setLevel(LOG_LEVEL)

    run = logging.getLogger("run")
    run.propagate = False
    run.setLevel(LOG_LEVEL)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    listener = None

    if LOG_DEST == LogDest.FILE:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=LOG_FILE, maxBytes=LOG_FILE_SIZE, backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)

        listener = logging.handlers.QueueListener(queue, file_handler)
        queue_handler = logging.handlers.QueueHandler(queue)

        dp_agent.addHandler(queue_handler)
        run.handlers = [console_handler, queue_handler]
    else:
        dp_agent.addHandler(console_handler)
        run.handlers = [console_handler]

    try:
        if listener:
            listener.start()
        yield
    finally:
        if listener:
            listener.stop()
