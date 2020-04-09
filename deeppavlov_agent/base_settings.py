from .core.db import DataBase
from .core.state_manager import StateManager
from .core.workflow_manager import WorkflowManager


PIPELINE_CONFIG = 'pipeline_conf.json'

DB_CONFIG = 'db_conf.json'

WAIT_TIME = 0

OVERWRITE_LAST_CHANCE = None

OVERWRITE_TIMEOUT = None

PORT = 4242

TELEGRAM_TOKEN = ''

TELEGRAM_PROXY = ''

STATE_MANAGER_CLASS = StateManager

WORKFLOW_MANAGER_CLASS = WorkflowManager

DB_CLASS = DataBase

FORMATTERS_MODULE = None

CONNECTORS_MODULE = None

RESPONSE_LOGGER = True
