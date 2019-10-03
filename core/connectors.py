import asyncio
import aiohttp
import time
from typing import Dict, Callable, List, Any

from core.transport.base import ServiceGatewayConnectorBase


class HTTPConnector:
    def __init__(self, session: aiohttp.ClientSession, url: str, formatter: Callable, service_name: str):
        self.session = session
        self.url = url
        self.formatter = formatter
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        async with self.session.post(self.url, json=self.formatter([payload])) as resp:
            response = await resp.json()
            response_time = time.time()
            await callback(
                dialog_id=payload['id'], service_name=self.service_name,
                response={self.service_name: self.formatter(response[0], mode='out')},
                response_time=response_time
            )


class AioQueueConnector:
    def __init__(self, queue):
        self.queue = queue

    async def send(self, payload: Dict, **kwargs):
        await self.queue.put(payload)


class QueueListenerBatchifyer:
    def __init__(self, session, url, formatter, service_name, queue, batch_size):
        self.session = session
        self.url = url
        self.formatter = formatter
        self.service_name = service_name
        self.queue = queue
        self.batch_size = batch_size

    async def call_service(self, process_callable):
        while True:
            batch = []
            rest = self.queue.qsize()
            for i in range(min(self.batch_size, rest)):
                item = await self.queue.get()
                batch.append(item)
            if batch:
                tasks = []
                async with self.session.post(self.url, json=self.formatter(batch)) as resp:
                    response = await resp.json()
                    response_time = time.time()
                for dialog, response_text in zip(batch, response):
                    tasks.append(process_callable(dialog['id'], self.service_name,
                                                  {self.service_name: self.formatter(response_text, mode='out')},
                                                  response_time))
                await asyncio.gather(*tasks)
            await asyncio.sleep(0.1)


class ConfidenceResponseSelectorConnector:
    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        response = payload['utterances'][-1]['selected_skills']
        best_skill = sorted(response.items(), key=lambda x: x[1]['confidence'], reverse=True)[0]
        response_time = time.time()
        await callback(
            dialog_id=payload['id'], service_name=self.service_name,
            response={
                'confidence_response_selector': {
                    'skill_name': best_skill[0],
                    'text': best_skill[1]['text'],
                    'confidence': best_skill[1]['confidence']
                }
            },
            response_time=response_time)


class HttpOutputConnector:
    def __init__(self, intermediate_storage: Dict, service_name: str):
        self.intermediate_storage = intermediate_storage
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        message_uuid = payload['message_uuid']
        event = payload['event']
        response_text = payload['dialog']['utterances'][-1]['text']
        self.intermediate_storage[message_uuid] = response_text
        event.set()
        response_time = time.time()
        await callback(payload['dialog']['id'], self.service_name,
                       response_text, response_time)


class EventSetOutputConnector:
    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        event = payload.get('event', None)
        if not event or not isinstance(event, asyncio.Event):
            raise ValueError("'event' key is not presented in payload")
        event.set()
        response_time = time.time()
        await callback(payload['dialog']['id'], self.service_name,
                       " ", response_time)


class AgentGatewayOutputConnector:
    _to_channel_callback: Callable

    def __init__(self, to_channel_callback: Callable):
        self._to_channel_callback = to_channel_callback

    async def send(self, payload: Dict, **kwargs):
        await self._to_channel_callback(payload)


class ServiceGatewayHTTPConnector(ServiceGatewayConnectorBase):
    _session: aiohttp.ClientSession
    _url: str

    def __init__(self, config: dict, formatter: Callable) -> None:
        super(ServiceGatewayHTTPConnector, self).__init__(config, formatter)
        self._session = aiohttp.ClientSession()
        self._url = config['url']

    async def send_to_service(self, dialogs: List[Dict]) -> List[Any]:
        with await self._session.post(self._url, json=self._formatter(dialogs)) as resp:
            responses_batch = await resp.json()

        return [self._formatter(response, mode='out') for response in responses_batch]



