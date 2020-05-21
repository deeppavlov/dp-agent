These types of dialog services can be connected to the agent's conversational pipeline:

    *  **Annotator**
    *  **Skill Selector**
    *  **Skills**
    *  **Response Selector**
    *  **Postprocessor**


Input Format
============

All services should accept an input in an agent ``state`` format. This format is described `here <state_>`__.
If an input format of a service differs from the agent state format then a **formatter** function should be implemented.
This formatter function receives a request in agent state format and returns a request in format supported by the service. 

Output Format
=============

All services should provide an output in an agent ``state`` format. This format is described `here <state_>`__.
To use the same formatter for input and output set the ``mode=='out'`` flag.

Annotator
=========

Annotator service returns a free-form response.

For example, the NER annotator may return a dictionary with ``tokens`` and ``tags`` keys:

    .. code:: json

        {"tokens": ["Paris"], "tags": ["I-LOC"]}

Sentiment annotator can return a list of labels:

    .. code:: json

        ["neutral", "speech"]

Also, Sentiment annotator can return just a string:

    .. code:: json

        "neutral"

Skill Selector
==============

Skill Selector service should return a list of names for skills selected to generate a candidate response for a dialog.

For example:

    .. code:: json

        ["chitchat", "hello_skill"]


Skill
=====

Skill service should return a **list of dicts** where each dict corresponds to a single candidate response.
Each candidate response entry requires ``text`` and ``confidence`` keys.
The Skill can update **Human** or **Bot** profile.
To do this, it should pack these attributes into ``human_attributes`` and ``bot_attributes`` keys.

All attributes in ``human_attributes`` and ``bot_attributes`` will overwrite current **Human** and **Bot**
attribute values in agent state. And if there are no such attributes,
they will be stored under ``attributes`` key inside **Human** or **Bot**.

The minimum required response of a skill is a 2-key dictionary:


    .. code:: json

        [{"text": "hello",
          "confidence": 0.33}]

But it's possible to extend it with  ``human_attributes`` and ``bot_attributes`` keys:

    .. code:: json

        [{"text": "hello",
          "confidence": 0.33,
          "human_attributes":
            {"name": "Vasily"},
          "bot_attributes":
            {"persona": ["I like swimming.", "I have a nice swimming suit."]}}]

Everything sent to ``human_attributes`` and ``bot_attributes`` keys will update `user` field in the same
utterance for the human and in the next utterance for the bot. Please refer to agent state_ documentation for more information about the **User** object updates.

Also it's possible for a skill to send any additional key to the state:

    .. code:: json

        [{"text": "hello",
          "confidence": 0.33,
          "any_key": "any_value"}]


Response Selector
=================

Unlike Skill Selector, Response Selector service should select a *single* skill as a source of the
final version of response. The service returns a name of the selected skill, text (might be
overwritten from the original skill response) and confidence (also might be overwritten):

 .. code:: json

        {"skill_name": "chitchat",
         "text": "Hello, Joe!",
         "confidence": 0.3}

Also it's possible for a Response Selector to overwrite any ``human`` or ``bot`` attributes:

 .. code:: json

        {"skill_name": "chitchat",
         "text": "Hello, Joe!",
         "confidence": 0.3,
         "human_attributes": {"name": "Ivan"}}

Postprocessor
=============

Postprocessor service can rewrite an utterance selected by the Response Selector. For example, it can
take a user's name from the state and add it to the final answer.

If a response was modified by Postprocessor then a new version goes the ``text`` field of the final
utterance and shown to the user, and the utterance selected by Response Selector goes to the ``orig_text`` field.

 .. code:: json

        "Goodbye, Joe!"


.. _state: https://deeppavlov-agent.readthedocs.io/en/latest/_static/api.html
