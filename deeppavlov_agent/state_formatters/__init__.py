from .dp_formatters import *
from .output_formatters import *

all_formatters = {
    'base_last_utterances_formatter_in': base_last_utterances_formatter_in,
    'chitchat_formatter_in': chitchat_formatter_in,
    'odqa_formatter_in': odqa_formatter_in,
    'chitchat_example_formatter_in': chitchat_example_formatter_in,
    'ner_formatter_out': ner_formatter_out,
    'sentiment_formatter_out': sentiment_formatter_out,
    'chitchat_odqa_formatter_out': chitchat_odqa_formatter_out,
    'add_confidence_formatter_out': add_confidence_formatter_out,
    'chitchat_example_formatter_out': chitchat_example_formatter_out,
    'base_hypotheses_formatter_in': base_hypotheses_formatter_in,
    'http_debug_output_formatter': http_debug_output_formatter,
    'http_api_output_formatter': http_api_output_formatter,
    'all_hypotheses_formatter_in': all_hypotheses_formatter_in
}
