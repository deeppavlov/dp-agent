import asyncio
import aiohttp
import time
from typing import Dict, Callable


class HTTPConnector:
    def __init__(self, session: aiohttp.ClientSession, url: str, formatter: Callable, service_name: str):
        self.session = session
        self.url = url
        self.formatter = formatter
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        formatted_payload = self.formatter([payload])
        service_send_time = time.time()
        async with self.session.post(self.url, json=formatted_payload) as resp:
            response = await resp.json()
            service_response_time = time.time()
            await callback(
                dialog_id=payload['id'], service_name=self.service_name,
                response={self.service_name: self.formatter(response[0], mode='out')},
                service_send_time=service_send_time,
                service_response_time=service_response_time
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
                formatted_payload = self.formatter(batch)
                service_send_time = time.time()
                async with self.session.post(self.url, json=formatted_payload) as resp:
                    response = await resp.json()
                    service_response_time = time.time()
                for dialog, response_text in zip(batch, response):
                    tasks.append(
                        process_callable(
                            dialog_id=dialog['id'], service_name=self.service_name,
                            response={self.service_name: self.formatter(response_text, mode='out')},
                            service_send_time=service_send_time,
                            service_response_time=service_response_time))
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
        await callback(dialog_id=payload['dialog']['id'],
                       service_name=self.service_name,
                       response=response_text,
                       service_response_time=time.time())


class EventSetOutputConnector:
    def __init__(self, service_name: str):
        self.service_name = service_name

    async def send(self, payload: Dict, callback: Callable):
        event = payload.get('event', None)
        if not event or not isinstance(event, asyncio.Event):
            raise ValueError("'event' key is not presented in payload")
        event.set()
        await callback(dialog_id=payload['dialog']['id'],
                       service_name=self.service_name,
                       response=" ", service_response_time=time.time())
