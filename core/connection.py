from mongoengine import connect
from agent_orange.config import config


db_host = config['agent']['database']['host']
db_port = config['agent']['database']['port']
db_name = f'{config["agent_namespace"]}_{config["agent"]["name"]}'

state_storage = connect(host=db_host, port=db_port, db=db_name)
