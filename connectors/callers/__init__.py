from connectors.callers.http import SimpleHttpServiceCaller


callers_map = {
    'simple_http_caller': {
        'caller': SimpleHttpServiceCaller,
        'description': 'Simple http/https service caller'
    }
}
