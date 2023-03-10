from ..parse_config import PipelineConfigParser
from ..core.state_manager import FakeStateManager


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
