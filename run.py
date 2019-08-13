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


async def test_infer_agent(agent: Agent) -> None:
    await agent.on_channel_message('Hello!', 'cmd_client', 'user', True)


def run_agent() -> None:
    async def on_serivce_message(partial_dialog_state: dict) -> None:
        await _agent.on_service_message(partial_dialog_state)

    async def send_to_service(service: str, dialog_state: dict) -> None:
        await _gateway.send_to_service(service, dialog_state)

    # TODO: integrate with channel connectors via Transport Gateway
    async def send_to_channel(channel_id: str, user_id: str, message: dict) -> None:
        print(f'<< Outgoing message [{str(message)}] to channel [{channel_id}] from user [{user_id}]')

    _agent = Agent(config=config, to_service_callback=send_to_service, to_channel_callback=send_to_channel)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['gateway']
    _gateway: TTransportGateway = gateway_cls(config=config, on_service_callback=on_serivce_message)

    loop = asyncio.get_event_loop()
    loop.create_task(test_infer_agent(_agent))
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
