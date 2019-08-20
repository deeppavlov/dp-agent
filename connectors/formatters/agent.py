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


def max_conf_response_selector(data: List[Dict]) -> List[Dict[str, str]]:
    selected_skills_batch = []

    for dialog_state in data:
        last_utterance = dialog_state['utterances'][-1]
        skill_responses = last_utterance['selected_skills']
        selected_skill = skill_responses[0]

        for skill_response in skill_responses[1:]:
            if skill_response['confidence'] > selected_skill['confidence']:
                selected_skill = skill_response

        selected_skills_batch.append(selected_skill)

    return selected_skills_batch


def test_response_formatter(data: List[Dict]) -> List[Dict[str, str]]:
    formatted_responses_batch = []

    for dialog_state in data:
        last_utterance = dialog_state['utterances'][-1]
        orig_text = last_utterance['orig_text']
        formatted_text = f'Agent issued response: {orig_text}'
        formatted_responses_batch.append({'formatted_text': formatted_text})

    return formatted_responses_batch
