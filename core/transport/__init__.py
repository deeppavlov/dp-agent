from typing import Optional, Tuple
from collections import namedtuple


ConfigItem = namedtuple('ConfigItem', ['type', 'description'])


class DummyConfig:
    _config: dict
    _config_schema = {
        'general': {
            'agent_name': ConfigItem(str, 'name which can unique identify agent in your landscape'),
            'transport': ConfigItem(str, 'transport solution name from config/transport keys')
        },
        'services': {
            'annotators': [
                {
                    'name': ConfigItem(str, 'annotator service name'),
                    'stateful': ConfigItem(bool, 'stateful annotator flag')
                }
            ],
            'skills': [
                {
                    'name': ConfigItem(str, 'annotator service name'),
                    'stateful': ConfigItem(bool, 'stateful annotator flag')
                }
            ]
        },
        'transport': {
            'rabbitmq': {
                'host': ConfigItem(str, 'rabbitmq host'),
                'port': ConfigItem([int, str], 'rabbitmq port')
            }
        }
    }

    def __init__(self, config: dict) -> None:
        self._config = config

    @staticmethod
    def _compare_dicts(pattern_dict: dict, sample_dict: dict) -> Tuple[bool, Optional[str]]:
        return True, None

    def _validate_structure(self, config: dict) -> None:
        pass

    def _validate(self, config: dict) -> None:
        pass
