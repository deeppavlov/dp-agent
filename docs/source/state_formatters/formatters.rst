**Formatters** are the functions that allow converting the input and output API of services into Agent's API.

Defining the formatters
=======================

There are two main formatter types: which extracts data from dict representation of dialogs and formats it to
service accessible form (dialog formatter), and which extracts data from service response and formats it prior
adding to state (response formatter, this is optional one)

**Dialog formatters**

This functions should accept a single parameter: dialog (in dict form), and return a list of tasks for service processing.
Each task should be in a format, which is correct for associated service.
From a dict form of a dialog you can extract data on:

  * Human - ``dialog['human']``
  * Bot - ``dialog['bot']``
  * List of all utterances - ``dialog['utterances']``
  * List of only human utterances - ``dialog['human_utterances']``
  * List of only bot utterances - ``dialog['bot_utterances']``

Each utterance (both bot and human) have some amount of same parameters:

  * Text - ``utterance['text']``
  * Annotations - ``utterance['annotations']``
  * User (human or bot, depending on type of utterance) - ``utterance['user']``

Human utterance have an additional parameters:

  * List of hypotheses - ``utterance['hypotheses']``
  * Additional attributes - ``utterance['attributes']``

Bot utterance also have additional attributes:

  * Active skill name (skill, which provided actual response) - ``utterance['active_skill']``
  * Response confidence - ``utterance['confidence']``
  * Original response text (not modified by postprocessors) - ``utterance['orig_text']``

**Response formatters**

This functions should accept one sample of skill response, and re-format it, making further processing available.
This formatters are optional.
