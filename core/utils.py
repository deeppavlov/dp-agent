import asyncio
from functools import partial
from typing import Callable, Awaitable


def run_sync_in_executor(func: Callable, *args, **kwargs) -> Awaitable:
    loop = asyncio.get_event_loop()
    if kwargs:
        func = partial(func, **kwargs)
    return loop.run_in_executor(None, func, *args)
