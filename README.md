# Agent
**Installation**
1. `cd` to `dp-agent`
2. Create virtual environment: `virtualenv env -p python3.6`
3. Activate virtual environment: `source env/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Run setup script: `python setup.py develop`


**Run via docker-compose**

**Demo dir** is `dp-agent/deployment/ner_chitchat` if you want to use cloud DP models
or `dp-agent/deployment/ner_chitchat_local` if you want to run all services locally 
(warning: ~25GB free RAM required to run all models locally).

1. `cd` to demo dir
2. Run `docker-compose build`
3. Run `docker-compose up`
4. Wait until services initialisation (`chitchat` usually initialises last with this
message: `chitchat| * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)`)

In other terminal to interact with bot:

5. `cd` to `dp-agent`
6. Activate virtual environment: `source env/bin/activate`
7. Run `python core/run.py channel -c cmd_client --config deployment/ner_chitchat/config.yaml`
(or if running all services locally: `python core/run.py channel -c cmd_client --config deployment/ner_chitchat_local/config.yaml`)
8. To turn off run `docker-compose down` from demo dir
