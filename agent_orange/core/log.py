import logging
import logging.config
from pathlib import Path

from agent_orange.config import config


def init_logger():
    log_config = config['logging']
    configured_loggers = [log_config.get('root', {})] + [logger for logger in
                                                         log_config.get('loggers', {}).values()]

    used_handlers = {handler for log in configured_loggers for handler in log.get('handlers', [])}

    for handler_id, handler in list(log_config['handlers'].items()):
        if handler_id not in used_handlers:
            del log_config['handlers'][handler_id]
        elif 'filename' in handler.keys():
            filename = handler['filename']
            logfile_path = Path(filename).expanduser().resolve()
            handler['filename'] = str(logfile_path)

    logging.config.dictConfig(log_config)
