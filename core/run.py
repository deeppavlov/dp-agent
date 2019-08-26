import asyncio
import argparse
from pathlib import Path

from core.config import get_config
from core.agent import Agent
from core.transport import transport_map
from core.channels import channels_map
from core.transport.base import TAgentGateway, TServiceCaller, TServiceGateway, TChannelConnector, TChannelGateway
from connectors.callers import callers_map
from connectors.formatters import formatters_map


parser = argparse.ArgumentParser()
parser.add_argument('mode', help='select agent component type', type=str, choices={'agent', 'service', 'channel'})
parser.add_argument('-c', '--channel', help='channel id', type=str, choices={'cmd_client'})
parser.add_argument('-n', '--service-name', help='service name', type=str)
parser.add_argument('-i', '--instance-id', help='service instance id', type=str, default='')
parser.add_argument('--config', help='path to config', type=str, default='')


# TODO: check all async type annotations


def run_agent(config: dict) -> None:
    async def on_service_message(partial_dialog_state: dict) -> None:
        await _agent.on_service_message(partial_dialog_state=partial_dialog_state)

    async def send_to_service(service_name: str, dialog_state: dict) -> None:
        await _gateway.send_to_service(service_name=service_name, dialog_state=dialog_state)

    async def on_channel_message(utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        await _agent.on_channel_message(utterance=utterance,
                                        channel_id=channel_id,
                                        user_id=user_id,
                                        reset_dialog=reset_dialog)

    async def send_to_channel(channel_id: str, user_id: str, response: str) -> None:
        await _gateway.send_to_channel(channel_id=channel_id, user_id=user_id, response=response)

    _agent = Agent(config=config, to_service_callback=send_to_service, to_channel_callback=send_to_channel)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['agent']
    _gateway: TAgentGateway = gateway_cls(config=config,
                                          on_service_callback=on_service_message,
                                          on_channel_callback=on_channel_message)


def run_service(config: dict) -> None:
    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['service']

    formatter_name = config['service']['connector_params']['formatter']
    formatter: callable = formatters_map[formatter_name]['formatter']

    caller_name = config['service']['connector_params']['caller']
    caller_name = formatters_map[formatter_name]['default_caller'] if caller_name == 'default' else caller_name
    caller_cls = callers_map[caller_name]['caller']

    _service_caller: TServiceCaller = caller_cls(config=config, formatter=formatter)
    _gateway: TServiceGateway = gateway_cls(config=config, service_caller=_service_caller)


def run_channel(config: dict) -> None:
    async def on_channel_message(utterance: str, channel_id: str, user_id: str, reset_dialog: bool) -> None:
        await _gateway.send_to_agent(utterance=utterance,
                                     channel_id=channel_id,
                                     user_id=user_id,
                                     reset_dialog=reset_dialog)

    async def send_to_channel(user_id: str, response: str) -> None:
        await _channel_connector.send_to_channel(user_id=user_id, response=response)

    transport_type = config['transport']['type']
    gateway_cls = transport_map[transport_type]['channel']

    _channel_id = config['channel']['id']
    connector_cls = channels_map[_channel_id]

    _gateway: TChannelGateway = gateway_cls(config=config, to_channel_callback=send_to_channel)
    _channel_connector: TChannelConnector = connector_cls(config=config, on_channel_callback=on_channel_message)


def main():
    args = parser.parse_args()
    mode = args.mode

    config_path = args.config
    config_path = Path(config_path).resolve() if config_path else None
    config = get_config(config_path)

    loop = asyncio.get_event_loop()

    if mode == 'agent':
        run_agent(config)

    elif mode == 'service':
        service_name = args.service_name
        instance_id = args.instance_id

        if service_name in config['services'].keys():
            service_config = config['services'][service_name]
            service_config['name'] = service_name
            service_config['instance_id'] = instance_id
            config['service'] = service_config
            run_service(config)
        else:
            raise ValueError(f'Settings for service {service_name} were not found in config file')

    elif mode == 'channel':
        channel_id = args.channel
        config['channels']['cmd_client'] = {}

        if channel_id in config['channels'].keys():
            channel_config = config['channels'][channel_id]
            channel_config['id'] = channel_id
            config['channel'] = channel_config
            run_channel(config)
        else:
            raise ValueError(f'Settings for channel {channel_id} were not found in config file')

    loop.run_forever()


if __name__ == '__main__':
    main()
