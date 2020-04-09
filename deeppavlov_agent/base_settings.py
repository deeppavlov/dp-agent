from .core.db import DataBase
from .core.state_manager import StateManager
from .core.workflow_manager import WorkflowManager
from .state_formatters.output_formatters import (
    http_api_output_formatter,
    http_debug_output_formatter
)

# Common parameters
DEBUG = True

# Basic agent configuration parameters
STATE_MANAGER_CLASS = StateManager
WORKFLOW_MANAGER_CLASS = WorkflowManager
DB_CLASS = DataBase

PIPELINE_CONFIG = 'pipeline_conf.json'
DB_CONFIG = 'db_conf.json'

OVERWRITE_LAST_CHANCE = None
OVERWRITE_TIMEOUT = None

FORMATTERS_MODULE = None
CONNECTORS_MODULE = None

RESPONSE_LOGGER = True

# HTTP app configuraion parameters
TIME_LIMIT = 0  # Without engaging the timeout by default

OUTPUT_FORMATTER = http_api_output_formatter
DEBUG_OUTPUT_FORMATTER = http_debug_output_formatter

# HTTP api run parameters
PORT = 4242

# Telegram client configuration parameters
TELEGRAM_TOKEN = ''
TELEGRAM_PROXY = ''
