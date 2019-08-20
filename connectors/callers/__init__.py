from connectors.callers.http import SimpleHttpServiceCaller
from connectors.callers.python import TestPythonScriptCaller


callers_map = {
    'simple_http_caller': {
        'caller': SimpleHttpServiceCaller,
        'description': 'Simple http/https service caller'
    },
    'test_python_caller': {
        'caller': TestPythonScriptCaller,
        'description': 'Test python script caller'
    }
}
