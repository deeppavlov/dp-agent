import asyncio
from typing import Any, Callable, Dict, List
from collections import defaultdict
from logging import getLogger
import os
import sys

import sentry_sdk
import aiohttp

from .transport.base import ServiceGatewayConnectorBase

logger = getLogger(__name__)
sentry_sdk.init(os.getenv("DP_AGENT_SENTRY_DSN"))


def get_size(obj, seen=None):
    """Recursively finds size of objects"""

    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)

    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, "__dict__"):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])

    return size


class HTTPConnector:
    def __init__(self, session: aiohttp.ClientSession, url: str, timeout: float):
        self.session = session
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def send(self, payload: Dict, callback: Callable):
        try:
            logger.warn(f"in {self.url} size_of {get_size(payload['payload'])}")
            async with self.session.post(self.url, json=payload["payload"], timeout=self.timeout) as resp:
                resp.raise_for_status()
                response = await resp.json()
            logger.warn(f"out {self.url} size_of {get_size(response)}")
            await callback(task_id=payload["task_id"], response=response[0])
        except Exception as e:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("payload", payload)
                scope.set_extra("url", self.url)
                sentry_sdk.capture_exception(e)
            logger.exception(Exception(e, {"payload": payload, "url": self.url}))
            response = e
            await callback(task_id=payload["task_id"], response=response)


class AioQueueConnector:
    def __init__(self, queue):
        self.queue = queue

    async def send(self, payload: Dict, **kwargs):
        await self.queue.put(payload)


class QueueListenerBatchifyer:
    def __init__(self, session, url, queue, batch_size):
        self.session = session
        self.url = url
        self.queue = queue
        self.batch_size = batch_size

    async def call_service(self, process_callable):
        while True:
            batch = []
            rest = self.queue.qsize()
            for _ in range(min(self.batch_size, rest)):
                item = await self.queue.get()
                batch.append(item)
            if batch:
                model_payload = self.glue_tasks(batch)

                logger.warn(f"in {self.url} batch size_of {get_size(model_payload)}")
                async with self.session.post(self.url, json=model_payload) as resp:
                    response = await resp.json()
                logger.warn(f"out {self.url} batch size_of {get_size(response)}")
                for task, task_response in zip(batch, response):
                    asyncio.create_task(process_callable(task_id=task["task_id"], response=task_response))
            await asyncio.sleep(0.1)

    def glue_tasks(self, batch):
        if len(batch) == 1:
            return batch[0]["payload"]
        else:
            result = {k: [] for k in batch[0]["payload"].keys()}
            for el in batch:
                for k in result.keys():
                    result[k].extend(el["payload"][k])
            return result


class ConfidenceResponseSelectorConnector:
    async def send(self, payload: Dict, callback: Callable):
        try:
            response = payload["payload"]["utterances"][-1]["hypotheses"]
            best_skill = max(response, key=lambda x: x["confidence"])
            await callback(task_id=payload["task_id"], response=best_skill)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)
            await callback(task_id=payload["task_id"], response=e)


class EventSetOutputConnector:
    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send(self, payload, callback: Callable):
        event = payload["payload"].get("event", None)
        if not event or not isinstance(event, asyncio.Event):
            raise ValueError("'event' key is not presented in payload")
        await callback(task_id=payload["task_id"], response=" ")
        event.set()


class AgentGatewayToChannelConnector:
    pass


class AgentGatewayToServiceConnector:
    _to_service_callback: Callable
    _service_name: str

    def __init__(self, to_service_callback: Callable, service_name: str):
        self._to_service_callback = to_service_callback
        self._service_name = service_name

    async def send(self, payload: Dict, **_kwargs):
        await self._to_service_callback(payload=payload, service_name=self._service_name)


class ServiceGatewayHTTPConnector(ServiceGatewayConnectorBase):
    _session: aiohttp.ClientSession
    _url: str
    _service_name: str

    def __init__(self, service_config: Dict) -> None:
        super().__init__(service_config)
        self._session = aiohttp.ClientSession()
        self._service_name = service_config["name"]
        self._url = service_config["url"]

    async def send_to_service(self, payloads: List[Dict]) -> List[Any]:
        batch = defaultdict(list)
        for payload in payloads:
            for key, value in payload.items():
                batch[key].extend(value)
        logger.warn(f"in {self.url} batch size_of {get_size(batch)}")
        async with await self._session.post(self._url, json=batch) as resp:
            responses_batch = await resp.json()
        logger.warn(f"out {self.url} batch size_of {get_size(responses_batch)}")

        return responses_batch


class PredefinedTextConnector:
    def __init__(self, response_text, annotations=None):
        self.response_text = response_text
        self.annotations = annotations or {}

    async def send(self, payload: Dict, callback: Callable):
        await callback(
            task_id=payload["task_id"], response={"text": self.response_text, "annotations": self.annotations}
        )


class PredefinedOutputConnector:
    def __init__(self, output):
        self.output = output

    async def send(self, payload: Dict, callback: Callable):
        await callback(task_id=payload["task_id"], response=self.output)
