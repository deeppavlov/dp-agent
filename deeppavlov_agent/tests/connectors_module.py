from typing import Dict, Callable

from ..core.connectors import Connector


class CustomOutputConnector(Connector):
    def __init__(self, output):
        self.output = output

    async def send(self, payload: Dict, callback: Callable) -> None:
        await callback(task_id=payload["task_id"], response=self.output)
