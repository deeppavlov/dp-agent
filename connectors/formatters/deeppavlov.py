from typing import Union, List, Dict


def format_dp_ner(data: Union[List[Dict], List[List[List[str]]]], out: bool) -> Union[Dict[str, List[str]], List[Dict]]:
    if out:
        service_responses = []

        for response in data:
            service_response = {}
            service_response['tokens'] = response[0]
            service_response['tags'] = response[1]
            service_responses.append(service_response)

        return service_responses

    else:
        payload = {}
        utterance_texts = []

        for dialog_state in data:
            last_utterance = dialog_state['utterances'][-1]
            utterance_text = last_utterance['text']
            utterance_texts.append(utterance_text)

        payload['context'] = utterance_texts

        return payload


def format_dp_ner_stand(data: Union[List[Dict], List[List[List[str]]]],
                        out: bool) -> Union[Dict[str, List[str]], List[Dict]]:
    if out:
        service_responses = []

        for response in data:
            service_response = {}
            service_response['tokens'] = response[0]
            service_response['tags'] = response[1]
            service_responses.append(service_response)

        return service_responses

    else:
        payload = {}
        utterance_texts = []

        for dialog_state in data:
            last_utterance = dialog_state['utterances'][-1]
            utterance_text = last_utterance['text']
            utterance_texts.append(utterance_text)

        payload['text1'] = utterance_texts

        return payload


def format_dp_odqa_stand(data: Union[List[Dict], List[List[str]]],
                        out: bool) -> Union[Dict[str, List[str]], List[Dict]]:
    if out:
        service_responses = []

        for response in data:
            service_response = {}
            service_response['text'] = response[0]
            service_response['confidence'] = response[1]
            service_response['name'] = None
            service_responses.append(service_response)

        return service_responses

    else:
        payload = {}
        utterance_texts = []

        for dialog_state in data:
            last_utterance = dialog_state['utterances'][-1]
            utterance_text = last_utterance['text']
            utterance_texts.append(utterance_text)

        payload['text1'] = utterance_texts

        return payload
