Built-in connectors
===================

Generally, connector is a python class with a method ``send``. It can be either a model, nn or rule based, or implementation of some transport protocols.
Although, we strongly recommend to implement nn models as an external services.

We have two different connectors for HTTP protocol as a built-in ones. Single sample and batchifying. Of course you can send a batch of samples to your model using single sample connector, but in this case you should form the batch with proper dialog formatter.
Batchifying connector will form batch from samples, available at the time, but can't guarantee actual batch size, only it's maximum size.

There are three more connectors, which can be used for different purposes. Each of them can be configurend as a *python* connector with it's name
You can read more on the connectors configuration in :ref:`connectors-config`.

Built-in python connectors
==========================

ConfidenceResponseSelectorConnector
-----------------------------------

This connector provides a simple response selection functionality. It chooses a best hypothesis based on its ``confidence`` parameter. In order to use it, you should consider a few things:

    * You don't need to define a dialog formatter (if you use built-in state manager)
    * You need to ensure, that all of your skills (or services with assighed ``add_hypothesis`` SM method) provides a ``confidence`` value somehow
    * It returns a chosen hypothesis, so you don't need to define output formatter as well
    * No special configuration parameters are needed

So the basic configuration for it is very simple:

.. code:: json

    {"response_selector": {
        "connector": {
            "protocol": "python",
            "class_name": "ConfidenceResponseSelectorConnector"
        },
        "state_manager_method": "add_bot_utterance",
        "previous_services": ["place previous skill names here"]
    }}

PredefinedTextConnector
-----------------------

This connector can be used in order to provide a simple way to answer in time, or in case of errors in your pipeline. It returns a basic parameters, which can be used to form a proper bot utterance.

    * ``text`` parameter will be a body of a bot utterance
    * Additionally, you can provide an ``annotations`` parameter, in case if you need to have a certain annotations for further dialog
    * There is no need to configure a dialog and response formatters

This example configuration represents simple last chance service:

.. code:: json

    {"last_chance_service": {
        "connector": {
            "protocol": "python",
            "class_name": "PredefinedTextConnector",
            "response_text": "Sorry, something went wrong inside. Please tell me, what did you say."
            "annotations": {"ner": "place your annotations here"}
        },
        "state_manager_method": "add_bot_utterance_last_chance",
        "tags": ["last_chance"]
    }}

More on last chance and timeout service configuration here:


PredefinedOutputConnector
-------------------------

This connector is quite similar to PredefinedTextConnector. It returns a predefined values, but instead of fixed ``text`` and ``annotations`` keys, it can be configured to return any arbitrary json compatible data structure.
The main purpose of this connector class is testing of pipeline routing, formatting or outputs. You can make a dummy service, which will imitate (in terms of structure) the response of desired model.
This connector have only one initialisation parameter:

    * ``output`` - list or dict, which will be passed to agent's callback as payload

This example configuration represents a dummy service, representing skill:

.. code:: json

    {"skill": {
        "connector": {
            "protocol": "python",
            "class_name": "PredefinedOutputConnector",
            "output": [{"text": "Hypotheses1", "confidence": 1}]
        },
        "dialog_formatter": "place your dialog formatter here",
        "response_formatter": "place your response formatter here",
        "state_manager_method": "add_hypothesis",
        "previous_services": ["list of the previous_services"]
    }}

But you can imitate any skill type with this connector.


Writing your own connectors
===========================

In order to define your own connector, you should follow these requirements:

    * It should be a python class
    * You can pass initialisation parameters to it via :ref:`connectors-config` python class
    * You need to implement an asynchronous method ``send(self, payload: Dict, callback: Callable)``
    * It should return a result to agent using ``callback`` function
    * ``payload`` input parameter is a dict of following structure:

.. code:: json

    {
        "task_id": "unique identifyer of processing task",
        "payload": "single task output, of the associated dialog formatter"
    }

So basically, your connector should look like this:

.. code:: python

    class MyConnector:
        def __init__(self, **kwargs):
            # Your code here

        async def send(self, payload: Dict, callback: Callable):
            try:
                # Write processing part here
                await callback(
                    task_id=payload['task_id'],
                    response=response  # Supposing that result of the processing is stored in a variable named "response"
                )
            except Exception as e:
                # That part allows agent to correctly process service internal errors
                # and call a "last chane" service without stopping the ongoing dialogs
                response = e
                await callback(
                    task_id=payload['task_id'],
                    response=response
                )
