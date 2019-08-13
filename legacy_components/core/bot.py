from legacy_components.core.state_schema import Bot
from legacy_components.core.connection import connect

try:
    BOT = Bot.objects(id__exact='5c7cf00e5c70e839bf9cb115')[0]
except IndexError:
    BOT = Bot(id='5c7cf00e5c70e839bf9cb115')
    BOT.save()
