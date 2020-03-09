Agent Configuration
======================

You can provide pipeline and database configuration for agent with config files. Both ``json`` and ``yml`` formats are acceptable.

**Config Description**

**Database**

Database configuration parameters are provided via ``db_conf`` file. Currently, agent runs on Mongo DB.

All default values are taken from `Mongo DB documentation <https://docs.mongodb.com/manual/>`__. Please refer to these docs if you need to
change anything.

Sample database config:

    .. code-block:: json

        {
            "env": false,
            "host": "mongo",
            "port": 27017,
            "name": "dp_agent"
        }

* **env**
    * If set to **false** (or not mentioned), exact parameters values will be used for db initialisation. Otherwise, agent will try to get an environmental variable by name, associated with parameter.
* **host**
    * A database host, or env variable, where database host name is stored
* **port**
    * A database port, or env variable, where database port is stored
* **name**
    * An name of the database, or env variable, where name of the database is stored


**Pipeline**

Pipeline configuration parameters are provided via ``pipeline_conf`` file. There are two different sections in config, which are used to configure Connectors and Services

**Services Config**

Service represents a single node of pipeline graph, or single step in processing of user message.
In ``pipeline_conf`` all services are grouped under "service" key.
Sample service config:

    .. code-block:: json

        {"group_name": {
                "service_label": {
                    "dialog_formatter": "dialog formatter",
                    "response_formatter": "response formatter",
                    "connector": "used connector",
                    "previous_services": "list of previous services",
                    "required_previous_services": "list of previous services",
                    "state_manager_method": "associated state manager method",
                    "tags": "list of tags"
                }
            }
        }

* **group name**
    * This is an optional key. If it is presented, you can mention services via their group name (in previous_services and required_previous_services)
    * In case if `group name` is presented, the actual service name will be ``<group name>.<service label>``
* **service_label**
    * Label of the service. Used as unique service name, if service is not grouped
    * Passed to state manager method, associated with service. So, service_label is saved in state
* **dialog_formatter**
    * Function, which extracts all the needed information from dialog and generate a list of tasks for sending to services
    * Can be configured in ``<python module name>:<function name>`` format
    * Formatter can produce several tasks from one dialog (for instance, you want to annotate all hypotheses)
    * Each task represents a single valid request payload, which can be processed by service without further formatting
* **response formatter**
    * Function, which re-formats a service response in a way, which is suitable for saving in dialog state
    * Can be configured in ``<python module name>:<function name>`` format
    * Optional parameter. Exact service output will be sent to state manager method, if that parameter is not presented
* **connector**
    * Function, which represents a connector to service. Can be configured here, or in Connectors
    * You can link a connector from `connectors` section by typing ``connectors.<connector name>``
* **previous_services**
    * List of name of services, which should be completed (or skipped, or respond with an error) before sending data to current service
    * Should contain either groups names or service names
* **required_previous_services**
    * List of names of services, which must be correctly completed before this service since their results are used in current service
    * If at least one of the required_previous_services is skipped or finished with error, current service will be skipped to
    * Should contain either groups names or service names
* **state_manager_method**
    * Name of the method of a StateManager class, which will be executed afterwards
* **tags**
    * Tags, associated with the service
    * Currently, tags are used in order to separate a service with specific behaviour
    * **selector** - this tag marks a skill selector service. It returns a list of skills, which are selected for further processing
    * **timeout** - this tag marks a timeout service, which will engage if deadline timestamp is presented and processing time exceeds it
    * **last_chance** - this tag marks a last chance service, which will engage if other services in pipeline have finished executing with an error, and further processing became impossible

**Connectors config**

Connector represents a function, where tasks are sent in order to process. Can be implementation of some data transfer protocol or model implemented in python.
Since agent is based on asynchronous execution, and can be slowed down by blocking synchronous parts, it is strongly advised to implement computational heavy services separate from agent, and use some protocols (like http) for data transfer.

There are several possibilities, to configure connector:

1. *Built-in HTTP*

    .. code:: json

        {"connector name": {
                "protocol": "http",
                "url": "connector url"
                "batch_size": "batch size for the service"
            }
        }

    * **connector name**
        * A name of the connector. Used in `services` part of the config, in order to associate service with the connector
    * **protocol**
        * http
    * **url**
        * Actual url, where an external service api is accessible. Should be in format ``http://<host>:<port>/<path>``
    * **batch_size**
        * Represents a maximum task count, which will be sent to a service in a batch. If not presented is interpreted as 1
        * If the value is 1, an `HTTPConnector <https://github.com/deepmipt/dp-agent/blob/master/deeppavlov_agent/core/connectors.py#L10>`__ class is used.
        * If the value is more than one, agent will use `AioQueueConnector <https://github.com/deepmipt/dp-agent/blob/master/deeppavlov_agent/core/connectors.py#L32>`__. That connector sends data to asyncio queue. Same time, worker `QueueListenerBatchifyer <https://github.com/deepmipt/dp-agent/blob/master/deeppavlov_agent/core/connectors.py#L40>`__, which collects data from queue, assembles batches and sends them to a service.


2. *Python class*

    .. code:: json

        {"connector name": {
                "protocol": "python",
                "class_name": "class name in 'python module name:class name' format",
                "other parameter 1": "",
                "other parameter 2": ""
            }
        }

    * **connector name**
        * Same as in HTTP connector case
    * **protocol**
        * python
    * **class_name**
        * Path to the connector's class in ``<python module name>:<class name>`` format
            * Connector's class should implement asynchronous ``send(self, payload: Dict, callback: Callable)`` method
            * ``payload represents`` a single task, provided by a dialog formatter, associated with service, alongside with ``task_id``: :code:`{'task_id': some_uuid, 'payload': dialog_formatter_task_data}`
            * ``callback`` is an asynchronous function `process <https://github.com/deepmipt/dp-agent/blob/master/deeppavlov_agent/core/agent.py#L58>`__. You should call that with service response and task_id after processing
    * **other parameters**
        * Any json compatible parameters, which will be passed to the connector class initialisation as ``**kwargs``
