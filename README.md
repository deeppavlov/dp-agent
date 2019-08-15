# Agent

*Run via docker-compose*

1. `cd` to `dp-agent/deployment/ner_chitchat`
2. `docker-compose up --build`
3. Wait until models initialisation
4. `cd` back to `dp-agent`
5. Run in other terminal to interac with bot:
`python core/run.py agent -c cmd --config deployment/ner_chitchat/agent_config.yaml`
6. To turn off run `docker-compose down`
