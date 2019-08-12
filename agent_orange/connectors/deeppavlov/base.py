from typing import List, Dict, Optional
from abc import abstractmethod

import requests

from agent_orange.core.transport.base import ServiceCallerBase


class AbstractDeepPavlovHttp(ServiceCallerBase):
    _url: str
    _model_args: List[str]

    def __init__(self, config: dict) -> None:
        self._url = config['service']['connector_params']['url']
        model_args = self._url = config['service']['connector_params']['url'].get('model_args', ['context'])
        self._model_args = model_args

    def _request(self, payload: Dict[List[str]]) -> Optional[List[List[List]]]:
        try:
            response = requests.post(self._url, json=payload)
            result = response.json() if response.status_code == 200 else None
        except requests.ConnectTimeout:
            result = None

        return result

    @abstractmethod
    def infer(self, dialog_states_batch: List[dict]) -> List[dict]:
        pass
