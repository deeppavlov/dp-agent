from logging import getLogger
from typing import Union, List, Dict, Any, Callable

from core.transport.base import ServiceCallerBase


logger = getLogger(__name__)


class TestPythonScriptCaller(ServiceCallerBase):
    def __init__(self,
                 config: dict,
                 formatter: Callable[[Union[List[Dict], Any], bool], Union[Any, List[Any]]]) -> None:

        super(TestPythonScriptCaller, self).__init__(config, formatter)
        logger.info(f'TestPythonScriptCaller connector for service {self._service_name} initiated')

    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        partial_dialog_states_batch = []
        responses_batch = self._formatter(dialog_states_batch)

        for i, response in enumerate(responses_batch):
            partial_state = {}
            partial_state['id'] = dialog_states_batch[i]['id']
            partial_state['utterances'] = []

            last_utterance_id = dialog_states_batch[i]['utterances'][-1]['id']
            partial_last_utterance = {}
            partial_last_utterance['id'] = last_utterance_id
            partial_last_utterance['service_responses'] = {}
            partial_last_utterance['service_responses'][self._service_name] = response

            partial_state['utterances'].append(partial_last_utterance)
            partial_dialog_states_batch.append(partial_state)

        return partial_dialog_states_batch
