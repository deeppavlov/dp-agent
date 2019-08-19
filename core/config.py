import yaml
from pathlib import Path
from typing import Optional


ERR_MSG_TEMPLATE = 'Agent config verification error: {}'


def get_config(config_path: Optional[Path] = None) -> dict:
    config_path = config_path or Path(__file__).resolve().parent / 'config.yaml'

    with config_path.open('r') as f:
        config = yaml.safe_load(f)

    verify(config)
    return config


def verify(config: dict) -> None:
    verify_pipeline(config)


def verify_pipeline(config: dict) -> None:
    pipeline = config['agent']['pipeline']
    type_error_text = 'Pipeline elements should be of List[str] types'

    if not isinstance(pipeline, dict):
        raise TypeError(ERR_MSG_TEMPLATE.format('Pipeline should be dict instance'))

    if len(pipeline) == 0:
        raise ValueError(ERR_MSG_TEMPLATE.format('Pipeline should not be empty'))

    for stage_name, services in pipeline.items():
        if not isinstance(services, list):
            raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))

        if not all(isinstance(service, str) for service in services):
            raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))

        if stage_name == 'skills' and not services:
            raise ValueError('Skills pipeline stage should contain at least one service')
