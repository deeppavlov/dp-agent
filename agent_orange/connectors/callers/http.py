from logging import getLogger
from typing import List, Dict, Callable, Union, Any

import requests

from agent_orange.core.transport.base import ServiceCallerBase


logger = getLogger(__name__)


class SimpleHttpServiceCaller(ServiceCallerBase):
    _session: requests.Session
    _url: str

    def __init__(self,
                 config: dict,
                 formatter: Callable[[Union[List[Dict], Any], bool], Union[Any, List[Dict]]]) -> None:

        super(SimpleHttpServiceCaller, self).__init__(config, formatter)
        self._session = requests.session()
        self._url = config['service']['connector_params']['url']
        logger.info(f'SimpleHttpServiceCaller connector for service {self._service_name} initiated')

    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        payload = self._formatter(data=dialog_states_batch, out=False)
        r = self._session.post(url=self._url, json=payload)

        if r.status_code != 200:
            raise RuntimeError(f'Service responded with {r.status_code} status code')

        formatted_result_batch = self._formatter(data=r.json(), out=True)
        partial_dialog_states_batch = []

        for i, result in enumerate(formatted_result_batch):
            partial_state = {}
            partial_state['id'] = dialog_states_batch[i]['id']
            partial_state['utterances'] = []

            last_utterance_id = dialog_states_batch[i]['utterances'][-1]['id']
            partial_last_utterance = {}
            partial_last_utterance['id'] = last_utterance_id
            partial_last_utterance['annotations'] = {}
            partial_last_utterance['annotations'][self._service_name] = result

            partial_state['utterances'].append(partial_last_utterance)
            partial_dialog_states_batch.append(partial_state)

        return partial_dialog_states_batch
