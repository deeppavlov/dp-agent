from ..core.connectors import make_connector
from ..core.service import make_service, Service
from ..core.state_manager import FakeStateManager


def test_make_service():
    service_name = "some_service"
    prev_service_name = "some_previous_service"
    required_prev_service_name = "some_required_previous_service_name"
    state_manager = FakeStateManager()
    connector, _ = make_connector(
        {"class_name": "PredefinedOutputConnector", "output": "Hello World!!!"}
    )
    connectors = {service_name: connector}
    service_names = {
        prev_service_name: set([prev_service_name]),
        required_prev_service_name: set([required_prev_service_name]),
    }

    service = make_service(
        name="some_service",
        state_manager=state_manager,
        connectors=connectors,
        service_names=service_names,
        config={
            "connector": "some_service",
            "state_manager_method": "add_annotation",
            "response_formatter": "base_last_utterances_formatter_in",
            "dialog_formatter": "http_api_output_formatter",
            "previous_services": [prev_service_name],
            "required_previous_services": [required_prev_service_name],
        },
    )

    assert isinstance(service, Service)
