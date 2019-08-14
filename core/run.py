import asyncio
import argparse
from pathlib import Path
from typing import Tuple

from core.config import get_config
from core.log import init_logger
from core.agent import Agent
from core.transport import transport_map
from core.transport.base import TTransportGateway, TServiceCaller, TTransportConnector
from connectors.callers import callers_map
from connectors.formatters import formatters_map


parser = argparse.ArgumentParser()
parser.add_argument('mode', help='select agent component type', type=str, choices={'agent', 'service', 'channel'})
parser.add_argument('-c', '--channel', help='channel type', type=str, choices={'cmd'})
parser.add_argument('-n', '--service-name', help='service name', type=str)
parser.add_argument('-i', '--instance-id', help='instance id', type=str, default='')
parser.add_argument('--config', help='path to config', type=str, default='')


def run_agent(config: dict) -> Tuple[Agent, TTransportGateway]:
    async def on_serivce_message(partial_dialog_state: dict) -> None:
        await agent.on_service_message(partial_dialog_state)

    async def send_to_service(service: str, dialog_state: dict) -> None:
        await gateway.send_to_service(service, dialog_state)

    # TODO: integrate with channel connectors via Transport Gateway
    async def send_to_channel(channel_id: str, user_id: str, message: str) -> None:
        # TODO: should we make async cmd_client mode less ad-hoc?
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


def run_service(config: dict) -> None:
    transport_type = config['transport']['type']
    connector_cls = transport_map[transport_type]['connector']

    formatter_name = config['service']['connector_params']['formatter']
    formatter: callable = formatters_map[formatter_name]['formatter']

    caller_name = config['service']['connector_params']['caller']
    caller_name = formatters_map[formatter_name]['default_caller'] if caller_name == 'default' else caller_name
    caller_cls = callers_map[caller_name]['caller']

    _service_caller: TServiceCaller = caller_cls(config=config, formatter=formatter)
    _connector: TTransportConnector = connector_cls(config=config, service_caller=_service_caller)


def run_cmd_client(config: dict) -> None:
    _agent, _gateway = run_agent(config)
    utterance = input('>> ')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_agent.on_channel_message(utterance=utterance,
                                                      channel_id='cmd_client',
                                                      user_id='cmd_client',
                                                      reset_dialog=True))


def main():
    args = parser.parse_args()
    mode = args.mode

    config_path = args.config
    config_path = Path(config_path).resolve() if config_path else None
    config = get_config(config_path)



    loop = asyncio.get_event_loop()

    if mode == 'agent':
        channel = args.channel

        if channel == 'cmd':
            run_cmd_client(config)
        else:
            run_agent(config)

    elif mode == 'service':
        service_name = args.service_name
        instance_id = args.instance_id

        if service_name in config['services'].keys():
            skill_config = config['services'][service_name]
            skill_config['name'] = service_name
            skill_config['instance_id'] = instance_id
            config['service'] = skill_config
            run_service(config)
        else:
            raise ValueError(f'Settings for service [{service_name}] were not found in config file')

    loop.run_forever()


if __name__ == '__main__':
    main()
