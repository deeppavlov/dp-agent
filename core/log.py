import logging
import logging.config
from datetime import datetime
from pathlib import Path

import yaml

from core.service import Service

agent_path = Path(__file__).resolve().parents[1]


def init_logger():
    log_config_path = agent_path / 'log_config.yml'

    with log_config_path.open('r') as f:
        log_config = yaml.safe_load(f)

    log_dir_path = agent_path / 'logs'
    log_dir_path.mkdir(exist_ok=True)

    configured_loggers = [log_config.get('root', {})] + [logger for logger in
                                                         log_config.get('loggers', {}).values()]

    used_handlers = {handler for log in configured_loggers for handler in log.get('handlers', [])}

    for handler_id, handler in list(log_config['handlers'].items()):
        if handler_id not in used_handlers:
            del log_config['handlers'][handler_id]
        elif 'filename' in handler.keys():
            filename = handler['filename']

            if filename[0] == '~':
                logfile_path = Path(filename).expanduser().resolve()
            elif filename[0] == '/':
                logfile_path = Path(filename).resolve()
            else:
                logfile_path = agent_path / filename

            handler['filename'] = str(logfile_path)

    logging.config.dictConfig(log_config)


class ResponseLogger:
    _enabled: bool
    _logger: logging.Logger

    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled
        if self._enabled:
            self._logger = logging.getLogger('service_logger')
            self._logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(agent_path / f'logs/{datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S_%f")}.log')
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter('%(message)s'))
            self._logger.addHandler(fh)

    def _log(self, task_id: str, workflow_record: dict, service: Service, status: str) -> None:
        service_name = service.name
        dialog_id = workflow_record['dialog'].id
        self._logger.info(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')}\t{dialog_id}\t{task_id}\t{status}\t{service_name}")

    def log_start(self, task_id: str, workflow_record: dict, service: Service) -> None:
        if self._enabled:
            self._log(task_id, workflow_record, service, 'start')

    def log_end(self, task_id: str, workflow_record: dict, service: Service) -> None:
        if self._enabled:
            self._log(task_id, workflow_record, service, 'end\t')