import asyncio
import argparse
from typing import Tuple

from core.config import config
from core.agent import Agent
from core.transport import transport_map
from core.transport.base import TTransportGateway, TServiceCaller, TTransportConnector
from connectors.callers import callers_map
from connectors.formatters import formatters_map


parser = argparse.ArgumentParser()
parser.add_argument('mode', help='select agent component type', type=str, choices={'agent', 'service', 'channel'})
parser.add_argument('-c', '--channel', help='channel type', type=str, choices={'cmd'})


def run_agent() -> Tuple[Agent, TTransportGateway]:
    async def on_serivce_message(partial_dialog_state: dict) -> None:
        await agent.on_service_message(partial_dialog_state)

    async def send_to_service(service: str, dialog_state: dict) -> None:
        await gateway.send_to_service(service, dialog_state)

    # TODO: integrate with channel connectors via Transport Gateway
    async def send_to_channel(channel_id: str, user_id: str, message: str) -> None:
        if channel_id == 'cmd_client':
            print(f'<< {message}')
            utterance = input('>> ')
            loop = asyncio.get_event_loop()
            loop.create_task(agent.on_channel_message(utterance, 'cmd_client', 'cmd_client', False))

    agent = Agent(config=config, to_service_callback=send_to_service, to_channel_callback=send_to_channel)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['gateway']
    gateway: TTransportGateway = gateway_cls(config=config, on_service_callback=on_serivce_message)

    return agent, gateway


def run_service() -> None:
    transport_type = config['transport']['type']
    connector_cls = transport_map[transport_type]['connector']

    formatter_name = config['service']['connector_params']['formatter']
    formatter: callable = formatters_map[formatter_name]['formatter']

    caller_name = config['service']['connector_params']['caller']
    caller_name = formatters_map[formatter_name]['default_caller'] if caller_name == 'default' else caller_name
    caller_cls = callers_map[caller_name]['caller']

    _service_caller: TServiceCaller = caller_cls(config=config, formatter=formatter)
    _connector: TTransportConnector = connector_cls(config=config, service_caller=_service_caller)


def run_cmd_client() -> None:
    _agent, _gateway = run_agent()
    utterance = input('>> ')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_agent.on_channel_message(utterance=utterance,
                                                      channel_id='cmd_client',
                                                      user_id='cmd_client',
                                                      reset_dialog=True))


def main():
    args = parser.parse_args()
    mode = args.mode
    channel = args.channel
    loop = asyncio.get_event_loop()

    if mode == 'agent':
        if channel == 'cmd':
            run_cmd_client()
        else:
            run_agent()

    elif mode == 'service':
        run_service()

    loop.run_forever()


if __name__ == '__main__':
    main()
