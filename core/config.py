import yaml
from pathlib import Path


ERR_MSG_TEMPLATE = 'Agent config verification error: {}'


_config_path = Path(__file__).resolve().parent / 'config.yaml'
with _config_path.open('r') as f:
    config = yaml.safe_load(f)


def verify(cfg: dict) -> None:
    verify_pipeline(cfg)


def verify_pipeline(cfg: dict) -> None:
    pipeline = cfg['agent']['pipeline']
    type_error_text = 'Pipeline elements should be of List[str] types'

    if not isinstance(pipeline, list):
        raise TypeError(ERR_MSG_TEMPLATE.format('Pipeline should be list instance'))

    if len(pipeline) == 0:
        raise ValueError(ERR_MSG_TEMPLATE.format('Pipeline should not be empty'))

    for services_group in pipeline:
        if not isinstance(services_group, list):
            raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))

        if len(services_group) == 0:
            raise ValueError(ERR_MSG_TEMPLATE.format('Services groups should not be empty'))

        if not all(isinstance(service, str) for service in services_group):
            raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))

    if len(pipeline[-1]) > 1:
        raise ValueError(ERR_MSG_TEMPLATE.format('Pipeline last services group should contain only one service'))


verify(config)
