from typing import Union, List, Dict


def format_agent_ranking_chitchat_prep(data: Union[List[Dict], Dict['str', List[Dict[str, str]]]],
                                       out: bool) -> Union[Dict[str, List[Dict]], List[Dict[str, str]]]:
    if out:
        service_responses = data['responses']
        return service_responses

    else:
        payload = {'dialogs': data}
        return payload


def format_chitchat_odqa_selector(data: Union[List[Dict], Dict['str', List[Dict[str, str]]]],
                                  out: bool) -> Union[Dict[str, List[Dict]], List[Dict[str, List[str]]]]:
    if out:
        service_responses = [{'skill_names': [response['skill_names']]} for response in data['responses']]
        return service_responses

    else:
        payload = {'dialogs': data}
        return payload
