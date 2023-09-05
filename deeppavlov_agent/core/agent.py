import os
import logging
import asyncio
from time import time
from typing import Any, Dict
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import sentry_sdk

from .pipeline import Pipeline
from .state_manager import StateManager
from .workflow_manager import WorkflowManager
from .service import Service

logger = logging.getLogger(__name__)

sentry_sdk.init(os.getenv("DP_AGENT_SENTRY_DSN"))  # type: ignore


class LocalResponseLogger:
    _enabled: bool
    _logger: logging.Logger

    def __init__(self, enabled: bool, cleanup_timedelta: int = 300) -> None:
        agent_path = Path(__file__).resolve().parents[1]

        self._services_load: Dict[str, int] = defaultdict(int)
        self._services_response_time: Dict[str, Dict[datetime, float]] = defaultdict(
            dict
        )
        self._tasks_buffer: Dict[str, datetime] = dict()
        self._enabled = enabled
        self._timedelta = timedelta(seconds=cleanup_timedelta)

        if self._enabled:
            self._logger = logging.getLogger("service_logger")
            self._logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(
                agent_path
                / f'logs/{datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S_%f")}.log'
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(fh)

    def _log(
        self,
        time: datetime,
        task_id: str,
        workflow_record: dict,
        service: Service,
        status: str,
    ) -> None:
        # service_name = service.name
        # dialog_id = workflow_record['dialog'].id
        # self._logger.info(
        #     f"{time.strftime('%Y-%m-%d %H:%M:%S.%f')}\t{dialog_id}\t{task_id}\t{status}\t{service_name}")
        pass

    def _cleanup(self, time):
        time_threshold = time - self._timedelta

        for key in list(self._tasks_buffer.keys()):
            if self._tasks_buffer[key] < time_threshold:
                del self._tasks_buffer[key]
            else:
                break

        for service_response_time in self._services_response_time.values():
            for start_time in list(service_response_time.keys()):
                if start_time < time_threshold:
                    del service_response_time[start_time]
                else:
                    break

    def log_start(self, task_id: str, workflow_record: dict, service: Service) -> None:
        start_time = datetime.utcnow()

        if service.is_input():
            self._services_load["agent"] += 1
            self._tasks_buffer[workflow_record["dialog"].id] = start_time
        elif not service.is_responder():
            self._tasks_buffer[task_id] = start_time
            self._services_load[service.label] += 1

        if self._enabled:
            self._log(start_time, task_id, workflow_record, service, "start")

    def log_end(
        self, task_id: str, workflow_record: dict, service: Service, cancelled=False
    ) -> None:
        end_time = datetime.utcnow()

        if service.is_responder():
            self._services_load["agent"] -= 1
            start_time = self._tasks_buffer.pop(workflow_record["dialog"].id, None)
            if start_time is not None and not cancelled:
                self._services_response_time["agent"][start_time] = (
                    end_time - start_time
                ).total_seconds()
        elif not service.is_input():
            start_time = self._tasks_buffer.pop(task_id, None)
            if start_time is not None:
                self._services_load[service.label] -= 1
                if not cancelled:
                    self._services_response_time[service.label][start_time] = (
                        end_time - start_time
                    ).total_seconds()
        self._cleanup(end_time)
        if self._enabled:
            self._log(end_time, task_id, workflow_record, service, "end\t")

    def get_current_load(self):
        self._cleanup(datetime.now())
        response_time = {}
        for service_name, time_dict in self._services_response_time.items():
            sm = sum(time_dict.values())
            ct = len(time_dict)
            response_time[service_name] = sm / ct if ct else 0
        response = {
            "current_load": dict(self._services_load),
            "response_time": response_time,
        }
        return response


# TODO: fix types
class Agent:
    _response_logger: LocalResponseLogger

    def __init__(
        self,
        pipeline: Pipeline,
        state_manager: StateManager,
        workflow_manager: WorkflowManager,
        enable_response_logger: bool,
    ) -> None:
        self.pipeline = pipeline
        self.state_manager = state_manager
        self.workflow_manager = workflow_manager
        self._response_logger = LocalResponseLogger(enable_response_logger)

    def flush_record(self, dialog_id: str):
        workflow_record = self.workflow_manager.flush_record(dialog_id)
        if workflow_record and "timeout_response_task" in workflow_record:
            workflow_record["timeout_response_task"].cancel()
        return workflow_record

    async def register_msg(
        self, utterance, deadline_timestamp=None, require_response=False, **kwargs
    ):
        dialog = await self.state_manager.get_or_create_dialog(**kwargs)
        dialog_id = str(dialog.id)
        service = self.pipeline.get_service_by_name("input")
        message_attrs = kwargs.pop("message_attrs", {})

        if require_response:
            event = asyncio.Event()
            kwargs["event"] = event
            kwargs["hold_flush"] = True

        self.workflow_manager.add_workflow_record(
            dialog=dialog, deadline_timestamp=deadline_timestamp, **kwargs
        )
        task_id = self.workflow_manager.add_task(dialog_id, service, utterance, 0)  # type: ignore
        self._response_logger.log_start(task_id, {"dialog": dialog}, service)  # type: ignore
        asyncio.create_task(
            self.process(task_id, utterance, message_attrs=message_attrs)
        )
        if deadline_timestamp:
            self.workflow_manager.set_timeout_response_task(
                dialog_id,
                asyncio.create_task(
                    self.timeout_process(dialog_id, deadline_timestamp)
                ),
            )

        if require_response:
            await event.wait()  # type: ignore
            return self.flush_record(dialog_id)

    async def process(self, task_id, response: Any = None, **kwargs):
        workflow_record, task_data = self.workflow_manager.complete_task(
            task_id, response, **kwargs
        )

        if task_data is None or workflow_record is None:
            logger.error("Task or workflow not exist. task_id={task_id}")
            return

        service = task_data["service"]  # type: ignore
        logger.info(
            (
                f"Received response from '{service.name}'. "
                f"task_id={task_id}; dialog_id={task_data['dialog']}; data={response}"
            )
        )

        # self._response_logger._logger.info(f"Service {service.label}: {response}")
        self._response_logger.log_end(task_id, workflow_record, service)

        if service.label in set(["last_chance_service", "timeout_service"]):
            # extract services from workflow_record and group them by status
            done = [
                k
                for k, v in workflow_record["services"].items()
                if v["done"] and not v.get("error", False)
            ]
            in_progress = [
                k
                for k, v in workflow_record["services"].items()
                if not v["done"] and not v.get("error", False)
            ]
            with_errors = [
                k
                for k, v in workflow_record["services"].items()
                if v.get("error", False)
            ]
            with sentry_sdk.push_scope() as scope:  # type: ignore
                scope.set_extra("user_id", workflow_record["dialog"].human.external_id)
                scope.set_extra("dialog_id", workflow_record["dialog"].id)
                scope.set_extra("response", response)
                scope.set_extra("done", done)
                scope.set_extra("in_progress", in_progress)
                scope.set_extra("with_errors", with_errors)
                sentry_sdk.capture_message(f"{service.label} was called")

        if isinstance(response, Exception):
            # Skip all services, which are depends on failured one
            for i in service.dependent_services:
                self.workflow_manager.skip_service(workflow_record["dialog"].id, i)
        else:
            response_data = service.apply_response_formatter(response)
            # Updating workflow with service response
            if service.state_processor_method:
                await service.state_processor_method(
                    dialog=workflow_record["dialog"],
                    payload=response_data,
                    label=service.label,
                    message_attrs=kwargs.pop("message_attrs", {}),
                    ind=task_data["ind"],  # type: ignore
                )

            # Processing the case, when service is a skill selector
            if service and service.is_sselector() and response_data:
                skipped_services = {
                    s
                    for s in service.next_services
                    if s.label not in set(response_data)
                }

                for s in skipped_services:
                    self.workflow_manager.skip_service(workflow_record["dialog"].id, s)

            # Flush record  and return zero next services if service is is_responder
            elif service.is_responder():
                if not workflow_record.get("hold_flush"):
                    self.flush_record(workflow_record["dialog"].id)
                return

        # Calculating next steps
        done, waiting, skipped = self.workflow_manager.get_services_status(  # type: ignore
            workflow_record["dialog"].id
        )
        next_services = self.pipeline.get_next_services(done, waiting, skipped)  # type: ignore

        await self.create_processing_tasks(workflow_record, next_services)

    async def create_processing_tasks(self, workflow_record, next_services):
        for service in next_services:
            tasks = service.apply_dialog_formatter(workflow_record)
            for ind, task_data in enumerate(tasks):
                dialog_id = workflow_record["dialog"].id

                task_id = self.workflow_manager.add_task(
                    dialog_id, service, task_data, ind
                )
                self._response_logger.log_start(task_id, workflow_record, service)  # type: ignore

                logger.info(
                    f"Send request to '{service.name}'. task_id={task_id}; dialog_id={dialog_id}; payload={task_data}."
                )

                self.workflow_manager.set_task_object(
                    workflow_record["dialog"].id,
                    task_id,
                    asyncio.create_task(
                        service.connector_func(
                            payload={"task_id": task_id, "payload": task_data},
                            callback=self.process,
                        )
                    ),
                )

    async def timeout_process(self, dialog_id, deadline_timestamp):
        await asyncio.sleep(deadline_timestamp - time())
        workflow_record = self.workflow_manager.get_workflow_record(dialog_id)
        if not workflow_record:
            return
        next_services = [self.pipeline.timeout_service]
        for k, v in self.workflow_manager.get_pending_tasks(dialog_id).items():  # type: ignore
            v["task_object"].cancel()
            self._response_logger.log_end(k, workflow_record, v["task_data"]["service"])

        await self.create_processing_tasks(workflow_record, next_services)
