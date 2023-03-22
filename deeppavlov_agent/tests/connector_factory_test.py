from ..core.connectors import (
    make_connector,
    HTTPConnector,
    PredefinedOutputConnector,
    AioQueueConnector,
)

from .connectors_module import CustomOutputConnector


def test_make_http_connector():
    connector, workers = make_connector(
        {"protocol": "http", "url": "http://some.url.com", "timeout": 1}
    )

    assert isinstance(connector, HTTPConnector)
    assert workers == []


def test_make_http_batch_connector_from_urllist():
    connector, workers = make_connector(
        {
            "protocol": "http",
            "urllist": ["http://some1.url.com", "http://some2.url.com"],
        }
    )

    assert isinstance(connector, AioQueueConnector)
    assert len(workers) == 2


def test_make_http_batch_connector_from_num_workers():
    connector, workers = make_connector(
        {"protocol": "http", "url": "http://some.url.com", "num_workers": 2}
    )

    assert isinstance(connector, AioQueueConnector)
    assert len(workers) == 2


def test_make_http_batch_connector_from_batch_size():
    connector, workers = make_connector(
        {"protocol": "http", "url": "http://some.url.com", "batch_size": 2}
    )

    assert isinstance(connector, AioQueueConnector)
    assert len(workers) == 1


def test_make_python_connector():
    connector, workers = make_connector(
        {"class_name": "PredefinedOutputConnector", "output": "Hello World!!!"},
    )

    assert isinstance(connector, PredefinedOutputConnector)
    assert workers == []


def test_make_python_connector_from_external_module():
    connector, workers = make_connector(
        {
            "class_name": "deeppavlov_agent.tests.connectors_module:CustomOutputConnector",
            "output": "Hello World!!!",
        },
    )

    assert isinstance(connector, CustomOutputConnector)
    assert workers == []
