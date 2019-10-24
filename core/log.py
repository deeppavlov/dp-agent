import logging
import logging.config
import re
from collections import defaultdict, namedtuple
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import List, Optional

import yaml

_root_path = Path(__file__).resolve().parents[1]
log_dir_path: Path = _root_path / 'logs'

AvgVals = namedtuple('AvgVals', ['name', 'agent', 'service'])


def init_logger() -> None:
    log_config_path = _root_path / 'log_config.yml'

    with log_config_path.open('r') as f:
        log_config = yaml.safe_load(f)

    configured_loggers = [log_config.get('root', {})] + [logger for logger in
                                                         log_config.get('loggers', {}).values()]

    used_handlers = {handler for log in configured_loggers for handler in log.get('handlers', [])}

    log_dir_path.mkdir(exist_ok=True)

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
                logfile_path = _root_path / filename

            handler['filename'] = str(logfile_path)

    logging.config.dictConfig(log_config)


class ResponseLogger:
    """Class to log Agent services response times and compute services RPS or average response time.

    Logs asre stored at `logs` directory. Class uses services and stats log files. Services timeouts are written to the
    services log file, services RPS/average response time are written to the `stats.log` file.

    """
    _log_agent: bool
    _log_service: bool
    _service_logger: logging.Logger
    _stats_logger: logging.Logger
    _log_file_path: Path

    def __init__(self, verbose: str, log_file_name: Optional[str] = None) -> None:
        """Inits logging parameters.

        Args:
            verbose: `agent` to log agent response timeout, `service` to log service response timeout, `both` to log
                both timeouts.
            log_file_name: Service timeouts log file name. If no argument is given new log file will be created with
                the name representing current detetime.

        Raises:
            ValueError: If wrong `verbose` argument or forbidden `log_file_name` was given.

        """
        self._stats_logger = logging.getLogger('stats_logger')
        self._log_agent = verbose == 'both' or verbose == 'agent'
        self._log_service = verbose == 'both' or verbose == 'service'

        if not self._log_agent and not self._log_service:
            raise ValueError('Neither agent time nor service time have chosen to log')

        if log_file_name == 'stats.log' or log_file_name == '':
            raise ValueError(f'"{log_file_name}" log file name is forbidden')

        service_log_file_name = log_file_name or datetime.strftime(datetime.utcnow(), '%Y-%m-%d_%H-%M-%S_%f.log')
        self._log_file_path = log_dir_path / service_log_file_name
        self._service_logger = self._get_service_logger()

    def __call__(self, workflow_record: dict) -> None:
        """Writes workflow record timeouts to the services log file.

        Besides the services present in the record, methods logs whole Agent pipeline timeout as time interval between
        `input` service send time and `cmd_responder` service done time.

        Args:
            workflow_record: Workflow record to be processed and logged.

        """
        for service_name, service_data in workflow_record['services'].items():
            result = [f'{service_name}']
            if self._log_agent:
                agent_done = service_data.get('agent_done_time')
                agent_send = service_data.get('agent_send_time')
                if agent_send and agent_done:
                    result.append(f'agent time {agent_done-agent_send} s')
            if self._log_service:
                service_done = service_data.get('service_done_time')
                service_send = service_data.get('service_send_time')
                if service_send and service_done:
                    result.append(f'service time {service_done-service_send} s')
            self._service_logger.info(', '.join(result))
        agent_send = workflow_record['services']['input']['agent_send_time']
        agent_done = workflow_record['services']['cmd_responder']['agent_done_time']
        self._service_logger.info(f'agent, agent time {agent_done-agent_send} s, service time {agent_done-agent_send}')

    def get_avg_time(self) -> None:
        """Writes average services timeouts to the stats log file."""
        self._stats_logger.info(f'Average response time for {self._log_file_path.name}:')
        avgtime = self._get_avg_time()
        self._log_stats(avgtime, 'mean', exponent_notation=True)

    def get_rps(self) -> None:
        """Writes services RPS to the stats log file."""
        self._stats_logger.info(f'Average responses per second for {self._log_file_path.name}:')
        rps = [AvgVals(avg_time.name,
                       1 / avg_time.agent if avg_time.agent else None,
                       1 / avg_time.service if avg_time.service else None) for avg_time in self._get_avg_time()]
        sort_by = 'agent' if self._log_agent else 'service'
        self._log_stats(rps, 'rps', key=lambda val: getattr(val, sort_by) or 0)

    def _get_avg_time(self) -> List[AvgVals]:
        """Calculates services average timeouts from the services log file."""
        agents = defaultdict(list)
        services = defaultdict(list)
        service_name_pattern = re.compile(r'(.+?),')
        agent_pattern = re.compile(r'.*agent time (.+?) s')
        service_pattern = re.compile(r'.*service time (.+?) s')
        with open(str(self._log_file_path), 'r') as logfile:
            for line in logfile:
                service_name = service_name_pattern.match(line)
                if service_name is None:
                    continue
                service_name = service_name.group(1)
                agent_time = agent_pattern.match(line)
                service_time = service_pattern.match(line)
                if agent_time:
                    agents[service_name].append(float(agent_time.group(1)))
                if service_time:
                    services[service_name].append(float(service_time.group(1)))
        agents = {key: mean(value) for key, value in agents.items()}
        services = {key: mean(value) for key, value in services.items()}
        response = []
        for key in set(agents.keys()) | set(services.keys()):
            response.append(AvgVals(key, agents.get(key), services.get(key)))
        return response

    def _get_service_logger(self) -> logging.Logger:
        """Initializes logger for services timeouts."""
        logger = logging.getLogger('service_logger')
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self._log_file_path)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(fh)
        return logger

    def _log_stats(self,
                   data: List[AvgVals],
                   param_name: str,
                   key: callable = lambda val: val.name,
                   exponent_notation: bool = False) -> None:
        """Writes services RPS or average timeouts to stats log file.

        Args:
            data: List with services metrics to write down.
            param_name: Name of service metrics.
            key: Key function to sort services in stats log file record. By default sorts services by name.
            exponent_notation: Sets metrics values format to exponent notation if True,
                to fixed-point notation otherwise.

        """
        fmt = lambda arg: f'{arg:.2e}' if exponent_notation else f'{arg:.2f}'
        format = lambda arg: fmt(arg) if isinstance(arg, float) else arg
        if len(data) > 0:
            max_name_length = max([len(argval.name) for argval in data])
            for avgval in sorted(data, key=key):
                result = [avgval.name.ljust(max_name_length)]
                if self._log_agent:
                    result.append(f'agent {param_name} {format(avgval.agent)}')
                if self._log_service:
                    result.append(f'service {param_name} {format(avgval.service)}')
                self._stats_logger.info('\t'.join(result))
