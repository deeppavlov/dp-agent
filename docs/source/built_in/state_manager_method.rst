Built-in StateManager
=====================

Built-in StateManager is responsible for all database read and write operations, and it's working with MongoDB database.
You can assign it's methods to services in your pipeline in order to properly save their responses to dialogs state.
You can read more on the pipeline configuration in :ref:`services-config`

Available methods
=================

Each of the methods have a following input parameters, which are filled automatically by agent during message processing.

    * ``dialog`` - dialog object, which will be updated
    * ``payload`` - response of the service with output formatter applied
    * ``label`` - label of the service
    * ``kwargs`` - minor arguments which are also provided by agent

You can use several state manager methods in your pipeline:

1. **add_annotation**
    * Adds a record to ``annotations`` section of the last utterance in dialog
    * ``label`` is used as a key
    * ``payload`` is used as a value

2. **add_annotation_prev_bot_utt**
    * Adds a record to ``annotations`` section of the second utterance from the end of the dialog
    * Only works if that utterance is bot utterance
    * Suitable for annotating last bot utterance on the next dialog round
    * ``label`` is used as a key
    * ``payload`` is used as a value

3. **add_hypothesis**
    * Adds a record to ``hypotheses`` section of the last utterance in dialog
    * Works only for human utterance, since bot utterance doesn't have such section
    * Accepts list of hypotheses dicts, provided by service
    * Two new keys are added to each hypothesis: ``service_name`` and ``annotations``
    * ``label`` is used as a value for ``service_name`` key
    * Empty dict is used as a value for ``annotations`` key

4. **add_hypothesis_annotation**
    * Adds an annotation to a single element of the ``hypotheses`` section of the last utterance in dialog under ``annotations`` key
    * In order to identify a certain hypothesis, it's index is used and stored in agent
    * ``label`` is used as a key
    * ``payload`` is used as a value

5. **add_text**
    * Adds a value to ``text`` field of the last utterance in dialog
    * Suitable for modifying a response in a bot utterance (original text can be found in ``orig_text`` field)
    * ``payload`` us used as a value

6. **add_bot_utterance**
    * This method is intended to be associated with response selector service
    * Adds a new bot utterance to the dialog
    * Modifies associated user and bot objects
    * We consider, that payload will be a single hypothesis, which was chosen as a bot response. So it will be parsed to different fields of bot utterance
    * ``text`` and ``orig_text`` fields of new bot utterance are filled with ``text`` value from payload
    * ``active_skill`` field is filled with ``skill_name`` value from payload
    * ``confidence`` field is filled with ``confidence`` value from payload
    * ``annotations`` from payload are copyed to ``annotations`` field of bot utterance
    * We expect, that skills will return ``text`` and ``confidence`` fields at least. ``skill_name`` and ``annotations`` are created within ``add_hypothesis`` method

7. **add_bot_utterance_last_chance**
    * This method is intended to be associated with a failure processing service, like timeout or last chance responder
    * It is very similar in processing to ``add_bot_utterance``, but it performs an additional check on the type of a last utterance in dialog
    * If the last utterance is a human utterance the method acts as an ``add_bot_utterance`` one
    * Otherwise, it will skip a stage with creating a new bot utterance and inserting it at the end of the dialog


There are two additional state manager methods, which are automatically assigned during agent's initialisation.

1. **add_human_utterance**
    * This method is assigned to an input service, which is created automatically during agent's initialisation process
    * Adds a new human utterance to the dialog
    * ``payload`` is used for ``text`` field of the new human utterance

2. **save_dialog**
    * This method is assigned to a responder service, which is created automatically during agent's initialisation process
    * It just saves a dialog to database
