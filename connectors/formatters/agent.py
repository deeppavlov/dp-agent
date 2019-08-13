from typing import Union, List, Dict


def format_agent_ranking_chitchat_prep(data: Union[List[Dict], Dict['str', List[Dict[str, str]]]],
                                       out: bool) -> Union[Dict[str, List[Dict]], List[str]]:
    if out:
        annotations = [f'{response["text"]}' for response in data['responses']]
        return annotations

    else:
        payload = {'dialogs': data}
        return payload
