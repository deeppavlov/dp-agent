Agent Configuration
====================

Configuration of pipeline and database for the **Agent** can be defined 
in ``json`` or ``yml`` file.

Database Config Description
===========================

Database configuration parameters are provided via ``db_conf`` file. Currently, agent supports Mongo DB.

All default values are taken from `Mongo DB documentation <https://docs.mongodb.com/manual/>`__. 
Please refer to these docs if you need to change anything.

Example of a database config:

    .. code-block:: json

        {
            "env": false,
            "host": "mongo",
            "port": 27017,
            "name": "dp_agent"
        }

* **env**
    * If set to **false** (or not mentioned), specified parameters' values will be used for db initialisation. Otherwise, agent will try to get an environmental variable by name, associated with parameter.
* **host**
    * A database host, or env variable, where database host name is stored.
* **port**
    * A database port, or env variable, where database port is stored.
* **name**
    * An name of the database, or env variable, where name of the database is stored.


Pipeline Config Description
===========================

Pipeline configuration parameters are specified in ``pipeline_conf`` file. 
There are two different sections in ``pipeline_conf`` to configure Connectors and Services.

.. _services-config:

**Services Config**
-------------------

Service is a single node of pipeline graph, or a single step in processing of user message.
In ``pipeline_conf`` all services are grouped under ``service`` key.

Example of a service config:

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
    * This is an optional key. If it is specified then services can be referenced by their `group name` in ``previous_services`` and ``required_previous_services``.
    * If `group name` is specified then the service name is ``<group name>.<service label>``.
* **service_label**
    * Label of the service. Used as a unique service name, if service is not grouped.
    * Passed to a state manager method, associated with the service. So,``service_label`` is saved in state.
* **dialog_formatter**
    * Generates list of tasks for services from a dialog state.
    * Can be configured as ``<python module name>:<function name>``.
    * Formatter can generate several tasks from the same dialog, for example, if you want to annotate all hypotheses.
    * Each generated task corresponds to a single valid request payload to be processed by service without further formatting.
* **response_formatter**
    * Maps a service response to the format of dialog state.
    * Can be configured as ``<python module name>:<function name>``.
    * Optional parameter. If not specified then unformatted service output is sent to state manager method.
* **connector**
    * Specifies a connector to a service. Can be configured here, or in `connectors` section.
    * Can be configured as ``<python module name>:<connector's class name>``.
* **previous_services**
    * List of services to be executed (or skipped, or respond with an error) before sending data to the service.
    * Should contain either group names or service names.
* **required_previous_services**
    * List of services to be completed correctly before the service, because it depends on their output.
    * If at least one of the ``required_previous_services`` is skipped or finished with an error, the service is not executed.
    * Should contain either group names or service names.
* **state_manager_method**
    * Name of a ``StateManager`` class method to be executed after the service response.
* **tags**
    * Tags, associated with the service to indicate a specific behaviour.
    * **selector** - corresponds to skill selector service. This service returns a list of skills selected for response generation. 
    * **timeout** - corresponds to timeout service. This service is called when processing time exceeds specified limit.
    * **last_chance** - corresponds to last chance service. This service is called if other services in pipeline have returned an error, and further processing is impossible.


.. _connectors-config:

**Connectors config**
---------------------

Connector represents a function, where tasks are sent in order to process. 
Can be implementation of some data transfer protocol or model implemented in python.
Since agent is based on asynchronous execution, and can be slowed down by blocking synchronous parts,
it is strongly advised to implement computational heavy services separate from agent, 
and use some protocols (like http) for data transfer.

There are several possibilities, to configure connector:

1. *Built-in HTTP*

    .. code:: json

        {"connector name": {
                "protocol": "http",
                "url": "connector url",
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
        * Represents a maximum task count, which will be sent to a service in a batch. If not specified is interpreted as 1
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
