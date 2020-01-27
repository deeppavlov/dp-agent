# Copyright 2017 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from logging import getLogger
from typing import List
import json

from deeppavlov.core.models.estimator import Component

logger = getLogger(__name__)


class JSON2StrList(Component):
    def __init__(self, **kwargs):
        pass

    def __call__(self, json_dump_of_data: List):
        logger.error(f"json_dump_of_data={json_dump_of_data}")
        payload = [json.loads(pl) for pl in json_dump_of_data]
        last_utterances = [pl["last_utterances"] for pl in payload]
        utterances_histories = [pl["utterances_histories"] for pl in payload]
        logger.error(f"last_utterances={last_utterances}")
        logger.error(f"utterances_histories={utterances_histories}")
        return ["123" for _ in last_utterances], [0.5 for _ in last_utterances]
