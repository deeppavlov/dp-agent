import pytest

from ..parse_config import PipelineConfigParser
from ..core.state_manager import FakeStateManager
from ..core import config
from ..core.config import is_service, is_connector


def test_config_must_be_a_dictionary():
    config_data = [{"services": {"annotator": {}}}]

    with pytest.raises(AssertionError):
        next(config.parse(config_data))


def test_parse_service_node():
    config_data = {"services": {"annotator": {"connector": "some_connector"}}}

    node = next(config.parse(config_data))
    assert is_service(node)
    assert node.path == ["services", "annotator"]


def test_parse_service_group():
    config_data = {
        "services": {
            "annotators": {
                "annotator1": {"connector": "some_connector"},
                "annotator2": {"connector": "some_connector"},
            }
        }
    }

    config_iter = config.parse(config_data)
    annotator1_node = next(config_iter)
    annotator2_node = next(config_iter)

    assert is_service(annotator1_node)
    assert annotator1_node.path == ["services", "annotators", "annotator1"]
    assert is_service(annotator2_node)
    assert annotator2_node.path == ["services", "annotators", "annotator2"]


def test_parse_connectors_group():
    config_data = {"connectors": {"some_connector": {"protocol": "http"}}}

    node = next(config.parse(config_data))
    assert is_connector(node)
    assert node.path == ["connectors", "some_connector"]


def test_parse_service_connector():
    config_data = {"services": {"annotator": {"connector": {"protocol": "http"}}}}
    config_iter = config.parse(config_data)

    connector_node = next(config_iter)
    service_node = next(config_iter)

    assert is_service(service_node)
    assert service_node.path == ["services", "annotator"]
    assert is_connector(connector_node)
    assert connector_node.path == ["services", "annotator", "connector"]


def test_service_is_enabled():
    config = {
        "services": {
            "annotator": {
                "connector": {
                    "protocol": "python",
                    "class_name": "PredefinedOutputConnector",
                    "output": {"body": "here are my annotations"},
                },
                "state_manager_method": "add_annotation",
                "is_enabled": True,
            },
        }
    }

    parsed_config = PipelineConfigParser(FakeStateManager(), config)

    service = list(filter(lambda x: x.label == "annotator", parsed_config.services))[0]

    assert service is not None


def test_service_is_disabled():
    config = {
        "services": {
            "annotator": {
                "connector": {
                    "protocol": "python",
                    "class_name": "PredefinedOutputConnector",
                    "output": {"body": "here are my annotations"},
                },
                "state_manager_method": "add_annotation",
                "is_enabled": False,
            },
        }
    }

    parsed_config = PipelineConfigParser(FakeStateManager(), config)

    assert len(parsed_config.services) == 0


def test_service_in_group_is_disabled():
    config = {
        "services": {
            "annotators": {
                "annotator1": {
                    "connector": {
                        "protocol": "python",
                        "class_name": "PredefinedOutputConnector",
                        "output": {"body": "annotations1"},
                    },
                    "state_manager_method": "add_annotation",
                },
                "annotator2": {
                    "connector": {
                        "protocol": "python",
                        "class_name": "PredefinedOutputConnector",
                        "output": {"body": "annotations2"},
                    },
                    "state_manager_method": "add_annotation",
                    "is_enabled": False,
                },
            }
        }
    }

    parsed_config = PipelineConfigParser(FakeStateManager(), config)
    filtered_services = list(
        filter(lambda x: x.label == "annotator2", parsed_config.services)
    )

    assert len(filtered_services) == 0
    assert len(parsed_config.services) == 1
