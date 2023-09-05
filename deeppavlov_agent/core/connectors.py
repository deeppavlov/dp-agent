import asyncio
import os
from typing import Any, Callable, Dict, List, Optional, Union, Tuple, cast
from typing_extensions import Protocol, runtime_checkable, Type
from collections import defaultdict
from logging import getLogger
from importlib import import_module


import sentry_sdk
import aiohttp

from .transport.settings import TRANSPORT_SETTINGS
from .transport.base import ServiceGatewayConnectorBase
from .transport.gateways.rabbitmq import RabbitMQAgentGateway
from .config import ConnectorConfig

logger = getLogger(__name__)
sentry_sdk.init(os.getenv("DP_AGENT_SENTRY_DSN"))  # type: ignore

logger = getLogger(__name__)
sentry_sdk.init(os.getenv('DP_AGENT_SENTRY_DSN'))


@runtime_checkable
class Connector(Protocol):
    async def send(self, payload: Dict, callback: Callable) -> None:
        ...


class HTTPConnector(Connector):
    def __init__(
        self, session: aiohttp.ClientSession, url: str, timeout: Optional[float] = 0
    ):
        self.session = session
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def send(self, payload: Dict, callback: Callable) -> None:
        try:
            async with self.session.post(
                self.url, json=payload["payload"], timeout=self.timeout
            ) as resp:
                resp.raise_for_status()
                response = await resp.json()
            await callback(task_id=payload["task_id"], response=response[0])
        except Exception as e:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("payload", payload)
                scope.set_extra("url", self.url)
                sentry_sdk.capture_exception(e)
            logger.exception(Exception(e, {"payload": payload, "url": self.url}))
            response = e
            await callback(task_id=payload["task_id"], response=response)


class AioQueueConnector(Connector):
    def __init__(self, queue):
        self.queue = queue

    async def send(self, payload: Dict, callback: Callable) -> None:
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
                async with self.session.post(self.url, json=model_payload) as resp:
                    response = await resp.json()
                for task, task_response in zip(batch, response):
                    asyncio.create_task(
                        process_callable(
                            task_id=task["task_id"], response=task_response
                        )
                    )
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


class ConfidenceResponseSelectorConnector(Connector):
    async def send(self, payload: Dict, callback: Callable) -> None:
        try:
            response = payload["payload"]["utterances"][-1]["hypotheses"]
            best_skill = max(response, key=lambda x: x["confidence"])
            await callback(task_id=payload["task_id"], response=best_skill)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.exception(e)

            await callback(task_id=payload["task_id"], response=e)


class EventSetOutputConnector(Connector):
    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send(self, payload, callback: Callable) -> None:
        event = payload["payload"].get("event", None)
        if not event or not isinstance(event, asyncio.Event):
            raise ValueError("'event' key is not presented in payload")
        await callback(task_id=payload["task_id"], response=" ")
        event.set()


class AgentGatewayToServiceConnector(Connector):
    _gateway: RabbitMQAgentGateway
    _service_name: str

    def __init__(self, gateway: RabbitMQAgentGateway, service_name: str) -> None:
        self._gateway = gateway
        self._service_name = service_name

    async def send(self, payload: Dict, callback: Callable) -> None:
        await self._gateway.send_to_service(
            payload=payload, service_name=self._service_name
        )


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
        async with await self._session.post(self._url, json=batch) as resp:
            responses_batch = await resp.json()

        return responses_batch


class PredefinedTextConnector(Connector):
    def __init__(self, response_text, annotations=None):
        self.response_text = response_text
        self.annotations = annotations or {}

    async def send(self, payload: Dict, callback: Callable) -> None:
        await callback(
            task_id=payload["task_id"],
            response={"text": self.response_text, "annotations": self.annotations},
        )


class PredefinedOutputConnector(Connector):
    def __init__(self, output):
        self.output = output

    async def send(self, payload: Dict, callback: Callable) -> None:
        await callback(task_id=payload["task_id"], response=self.output)


_BUILT_IN_CONNECTORS = {
    "PredefinedOutputConnector": PredefinedOutputConnector,
    "PredefinedTextConnector": PredefinedTextConnector,
    "ConfidenceResponseSelectorConnector": ConfidenceResponseSelectorConnector,
}


_SESSION: Optional[aiohttp.ClientSession] = None


def _get_session() -> aiohttp.ClientSession:
    global _SESSION

    if _SESSION is None:
        _SESSION = aiohttp.ClientSession()

    return _SESSION


_GATEWAY: Optional[RabbitMQAgentGateway] = None


def _get_gateway(
    on_channel_callback=None, on_service_callback=None
) -> RabbitMQAgentGateway:
    global _GATEWAY

    if _GATEWAY is None:
        _GATEWAY = RabbitMQAgentGateway(
            config=TRANSPORT_SETTINGS,
            on_service_callback=on_service_callback,
            on_channel_callback=on_channel_callback,
        )

    return _GATEWAY


def _make_http_connector(
    config: Union[ConnectorConfig, Dict]
) -> Tuple[Connector, List[QueueListenerBatchifyer]]:
    url = config.get("url")
    urllist = config.get("urllist")

    if not isinstance(url, str) and not isinstance(urllist, list):
        raise ValueError("url or urllist must be provided")

    if (
        "urllist" in config
        or "num_workers" in config
        or config.get("batch_size", 1) > 1
    ):
        workers = []
        queue: asyncio.Queue[Any] = asyncio.Queue()
        batch_size = config.get("batch_size", 1)
        urllist = urllist or ([url] * config.get("num_workers", 1))

        for url in urllist:
            workers.append(
                QueueListenerBatchifyer(
                    _get_session(), cast(str, url), queue, batch_size
                )
            )

        return AioQueueConnector(queue), workers

    return (
        HTTPConnector(
            session=_get_session(), url=cast(str, url), timeout=config.get("timeout")
        ),
        [],
    )


def _make_amqp_connector(
    config: Union[ConnectorConfig, Dict]
) -> Tuple[Connector, List[QueueListenerBatchifyer]]:
    service_name = config.get("service_name") or config["connector_name"]
    return (
        AgentGatewayToServiceConnector(
            gateway=_get_gateway(), service_name=service_name
        ),
        [],
    )


def _get_connector_class(class_name: str) -> Optional[Type[Any]]:
    params = class_name.split(":")
    connector_class: Optional[Type[Any]] = None

    if len(params) == 2:
        module = import_module(params[0])
        connector_class = getattr(module, params[1], None)
    elif len(params) == 1:
        connector_class = _BUILT_IN_CONNECTORS.get(params[0])

    return connector_class


def _make_connector_from_class(
    config: Union[ConnectorConfig, Dict]
) -> Tuple[Connector, List[QueueListenerBatchifyer]]:
    kwargs = {
        key: config[key] for key in config if key not in ["protocol", "class_name"]  # type: ignore
    }

    class_name = config["class_name"]
    connector_class = _get_connector_class(class_name)

    if not connector_class:
        raise ValueError(f"Connector class {class_name} not found")

    return connector_class(**kwargs), []


def make_connector(
    config: Union[ConnectorConfig, Dict]
) -> Tuple[Connector, List[QueueListenerBatchifyer]]:
    if config.get("class_name"):
        return _make_connector_from_class(config)

    if config.get("protocol") == "http":
        return _make_http_connector(config)

    # TODO: remove AMQP if it is not used
    if config.get("protocol") == "AMQP":
        return _make_amqp_connector(config)

    raise ValueError("invalid protocol or class_name")
