import pytest

from ..core.workflow_manager import WorkflowManager
from uuid import uuid4


class FakeDialog:
    def __init__(self, id):
        self.id = id


class FakeService:
    def __init__(self, name):
        self.name = name


def _create_workflow_with_dialog():
    workflow = WorkflowManager()
    dialog_id = uuid4().hex
    workflow.add_workflow_record(FakeDialog(dialog_id))

    return workflow, dialog_id


def test_internal_params():
    workflow, dialog_id = _create_workflow_with_dialog()

    assert dialog_id in workflow.workflow_records
    assert len(workflow.workflow_records) == 1


def test_add_duplicate_dialog():
    workflow, dialog_id = _create_workflow_with_dialog()

    with pytest.raises(ValueError):
        workflow.add_workflow_record(FakeDialog(dialog_id))


def test_flush_record():
    workflow, dialog_id = _create_workflow_with_dialog()
    workflow_record = workflow.flush_record(dialog_id)

    assert isinstance(workflow_record, dict)
    assert workflow_record["dialog"].id == dialog_id
    assert len(workflow.workflow_records) == 0


def test_add_task():
    workflow, dialog_id = _create_workflow_with_dialog()
    payload = uuid4().hex
    task_service = FakeService("FakeService")
    task_id = workflow.add_task(dialog_id, task_service, payload, 1)

    assert task_id is not None
    assert len(workflow.tasks) == 1
    assert task_id in workflow.tasks


def test_complete_task():
    workflow, dialog_id = _create_workflow_with_dialog()
    payload = uuid4().hex
    response = "123"
    task_service = FakeService("FakeService")
    task_id = workflow.add_task(dialog_id, task_service, payload, 1)
    workflow_record, task = workflow.complete_task(task_id, response)

    assert isinstance(task, dict)
    assert isinstance(workflow_record, dict)
    assert task["service"].name == task_service.name
    assert task["dialog"] == workflow_record["dialog"].id


def test_double_complete_task():
    workflow, dialog_id = _create_workflow_with_dialog()
    payload = uuid4().hex
    response = "123"
    task_service = FakeService("FakeService")
    task_id = workflow.add_task(dialog_id, task_service, payload, 1)
    workflow.complete_task(task_id, response)
    workflow_record, task = workflow.complete_task(task_id, response)

    assert workflow_record is None
    assert task is None


def test_next_tasks():
    workflow, dialog_id = _create_workflow_with_dialog()
    payload = uuid4().hex
    response = "123"
    done_service = FakeService(uuid4().hex)
    waiting_service = FakeService(uuid4().hex)
    skipped_service = FakeService(uuid4().hex)

    workflow.skip_service(dialog_id, skipped_service)
    task_id = workflow.add_task(dialog_id, done_service, payload, 1)
    workflow.complete_task(task_id, response)
    workflow.add_task(dialog_id, waiting_service, payload, 1)

    done, waiting, skipped = workflow.get_services_status(dialog_id)

    assert done_service.name in done
    assert waiting_service.name in waiting
    assert skipped_service.name in skipped


def test_flush():
    workflow, dialog_id = _create_workflow_with_dialog()
    payload = uuid4().hex
    response = "123"
    done_service = FakeService(uuid4().hex)
    waiting_service = FakeService(uuid4().hex)
    skipped_service = FakeService(uuid4().hex)

    workflow.skip_service(dialog_id, skipped_service)
    done_task_id = workflow.add_task(dialog_id, done_service, payload, 1)
    workflow.complete_task(done_task_id, response)
    waiting_task_id = workflow.add_task(dialog_id, waiting_service, payload, 1)

    workflow_record = workflow.flush_record(dialog_id)
    assert dialog_id == (workflow_record and workflow_record["dialog"].id)

    _, late_task = workflow.complete_task(waiting_task_id, response)
    assert "dialog" in late_task
    assert dialog_id == late_task["dialog"]
