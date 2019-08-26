# Agent
*Installation*
1. `cd` to `dp-agent`
2. Create virtual environment: `virtualenv env -p python3.6`
3. Activate virtual environment: `source env/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Run setup script: `python setup.py develop`


*Run via docker-compose*

1. `cd` to `dp-agent/deployment/ner_chitchat`
2. Run `docker-compose build`
3. Run `docker-compose up`
4. Wait until services initialisation (`chitchat` usually initialises last)

In other terminal to interact with bot:

5. `cd` to `dp-agent`
6. Activate virtual environment: `source env/bin/activate`
7. Run `python core/run.py channel -c cmd_client --config deployment/ner_chitchat/config.yaml`
8. To turn off run `docker-compose down` from `dp-agent/deployment/ner_chitchat` dir
