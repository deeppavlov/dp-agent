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
    type_error_text = 'Pipeline elements should be of str or List[str] types'

    for stage in pipeline:
        if isinstance(stage, list):
            if not all(isinstance(service, str) for service in stage):
                raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))
        elif not isinstance(stage, str):
            raise TypeError(ERR_MSG_TEMPLATE.format(type_error_text))

    if not isinstance(cfg[-1], str):
        raise TypeError(ERR_MSG_TEMPLATE.format('Pipeline last element should be only one service'))


verify(config)
