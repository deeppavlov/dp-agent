import asyncio
import argparse

from agent_orange.config import config
from agent_orange.core.agent import Agent
from agent_orange.core.transport import transport_map
from agent_orange.core.transport.base import TTransportGateway, TServiceCaller, TTransportConnector
from agent_orange.connectors.callers import callers_map
from agent_orange.connectors.formatters import formatters_map


parser = argparse.ArgumentParser()
parser.add_argument('mode', help='select agent component type', type=str, choices={'agent', 'service', 'channel'})
parser.add_argument('-c', '--channel', help='channel type', type=str, choices={'console'})


def run_agent() -> None:
    _agent: Agent
    _gateway: TTransportGateway

    async def on_serivce_message(partial_dialog_state: dict) -> None:
        await _agent.on_service_message(partial_dialog_state)

    async def send_to_service(service: str, dialog_state: dict) -> None:
        await _gateway.send_to_service(service, dialog_state)

    _agent = Agent(config=config, to_service_callback=send_to_service)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['gateway']
    _gateway = gateway_cls(config=config, on_service_callback=on_serivce_message)

    loop = asyncio.get_event_loop()
    loop.run_forever()


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

    loop = asyncio.get_event_loop()
    loop.run_forever()


def main():
    args = parser.parse_args()
    mode = args.mode

    if mode == 'agent':
        run_agent()
    if mode == 'service':
        run_service()


if __name__ == '__main__':
    main()
