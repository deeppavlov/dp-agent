from typing import Union, List, Dict


def format_dp_ner(data: Union[List[Dict], List[List[List[str]]]], out: bool) -> Union[Dict[str, List[str]], List[Dict]]:
    if out:
        annotations = []

        for response in data:
            annotation = {}
            annotation['tokens'] = response[0]
            annotation['tags'] = response[1]
            annotations.append(annotation)

        return annotations

    else:
        payload = {}
        utterance_texts = []

        for dialog_state in data:
            last_utterance = dialog_state['utterances'][-1]
            utterance_text = last_utterance['text']
            utterance_texts.append(utterance_text)

        payload['context'] = utterance_texts

        return payload
