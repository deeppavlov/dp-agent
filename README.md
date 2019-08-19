# Agent

*Run via docker-compose*

1. `cd` to `dp-agent/deployment/ner_chitchat`
2. Run `docker-compose build`
3. Run `docker-compose up`
4. Wait until services initialisation

In other terminal to interact with bot:

5. `cd` to `dp-agent`
6. Run `python core/run.py agent -c cmd --config deployment/ner_chitchat/agent_config.yaml`
7. To turn off run `docker-compose down` from `dp-agent/deployment/ner_chitchat` dir
