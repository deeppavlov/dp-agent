from core.channels.cmd import CmdConnector
from core.channels.telegram import TelegramConnector


channels_map = {
    'cmd_client': CmdConnector,
    'telegram': TelegramConnector
}
