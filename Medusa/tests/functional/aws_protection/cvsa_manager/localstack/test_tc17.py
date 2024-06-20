"""
TC82: No Upgrade for unconfigured instances
    1. Create unconfigured instance (using forced behavior)
    2. Verify that instance was stopped but Upgrade is not triggered
TC17: Backup request when cVSA is in maintenance mode during Upgrade
    Prerequisite: RolloutWorkflow set to: * * * * *, Time required to idle: 1m
    1. Verify that cVSA is in maintenance mode (cVSAMaintenanceEvent: Action=Started)
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    3. Ensure cVSAReadyEvent is received AFTER cVSAMaintentence: Action=Stopped with Success)
    4. Verify storeonce health state.
TC44: Backup / Restore request while Upgrade is in progress
    Prerequisite: At least two AMI images are available with different versions
    Prerequisite 2: RolloutWorkflow set to: * * * * *, Time required to idle: 1m
    1. Verify cvsa instance
    2. Send finished event to trigger update
    3. Verify update workflow starts (it do not need to be cadence check)
    4. Send restore request
    5. Verify instance stopped and terminated
    6. Verify new instance is created.
    7. Verify serial number is the same and the configuration is correct
    8. Verify that version is updated
"""

from typing import List

from kafka.protocol.message import Message
from pytest import mark

from lib.common.enums.cvsa import (
    StopReason,
    MaintenanceOperation,
    MaintenanceAction,
    TerminateReason,
    RequestFinishedStatus,
)
from lib.platform.cloud.cloud_dataclasses import CloudImage
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    get_amis_for_update,
    get_cvsa_version,
    verify_deployed_cvsa,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
    verify_ready_event,
    verify_no_event,
    verify_terminated_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.housekeeping_request_steps import (
    send_housekeeping_requested_event,
)
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event, verify_no_maintenance_event
from tests.steps.aws_protection.cvsa.restore_request_steps import (
    send_restore_requested_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
@mark.parametrize(
    "send_requested_event",
    [
        send_backup_requested_event,
        send_restore_requested_event,
        send_housekeeping_requested_event,
    ],
)
def test_tc17(kafka_mgr: KafkaManager, aws: CloudVmManager, send_requested_event):
    older_ami, newest_ami = get_amis_for_update(cloud_vm_mgr=aws)
    verify_instance_not_deployed_initially = True
    if send_requested_event == send_backup_requested_event:
        verify_unconfigured_instance_not_upgraded(kafka_mgr, older_ami)
        verify_instance_not_deployed_initially = False
    prepare_cvsa_instance_for_upgrade(kafka_mgr, aws, older_ami, verify_instance_not_deployed_initially)

    wait_for_cvsa_upgrade_start(kafka_mgr)
    kafka_mgr.correlation_id = kafka_mgr.generate_key()
    send_backup_requested_event(kafka_mgr, data_protected_gb=1, update_offsets=False)
    verify_events_during_maintenance(kafka_mgr)
    wait_for_cvsa_upgrade_finish(kafka_mgr, aws, newest_ami)

    verify_receiving_ready_event(kafka_mgr, send_requested_event)

    # Ensure that requested event was NOT processed during maintenance.
    maintenance_events = get_events_during_maintenance(kafka_mgr)
    if events_include_type(maintenance_events, ["cvsa.v1.CVSAResizedEvent", "cvsa.v1.CVSAReadyEvent"]):
        assert False, f"Received CVSAResizedEvent or CVSAReadyEvent during the maintenance phase."


def verify_unconfigured_instance_not_upgraded(kafka_mgr: KafkaManager, ami: CloudImage):
    send_backup_requested_event(
        kafka_mgr,
        ami=ami.id,
        data_protected_gb=1,
        headers={
            "ce_forcedunconfigured": bytes("true", "utf-8"),
        },
    )
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="failed due to forced behavior",
    )
    verify_stopped_event(kafka_mgr, reason=StopReason.UNHEALTHY)
    verify_no_maintenance_event(kafka_mgr, timeout=180)


def prepare_cvsa_instance_for_upgrade(
    kafka_mgr: KafkaManager, aws: CloudVmManager, ami: CloudImage, verify_not_deployed: bool
):
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws,
        kafka_mgr=kafka_mgr,
        data_protected_gb=1,
        ami=ami,
        headers={"ce_forcedupgradetimesec": bytes("30", "utf-8")},
        verify_not_deployed=verify_not_deployed,
    )
    verify_no_maintenance_event(kafka_mgr, timeout=180)
    verify_no_event(kafka_mgr, event_type="cvsa.v1.CVSAStoppedEvent")
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id, ami_version=ami.version)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)


def wait_for_cvsa_upgrade_start(kafka_mgr: KafkaManager):
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.UPGRADE,
    )


def wait_for_cvsa_upgrade_finish(kafka_mgr: KafkaManager, aws: CloudVmManager, ami: CloudImage):
    verify_maintenance_event(
        kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.UPGRADE,
    )
    cvsa_version = get_cvsa_version(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    assert cvsa_version == ami.version


def verify_receiving_ready_event(kafka_mgr: KafkaManager, send_event_function: callable):
    if send_event_function == send_housekeeping_requested_event:
        verify_ready_event(kafka_mgr, backup_streams=None)
    else:
        verify_ready_event(kafka_mgr)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)


def get_events_during_maintenance(kafka_mgr: KafkaManager) -> List[Message]:
    events_during_maintenance = []
    in_maintenance = False
    event_type_maintenance = "cvsa.v1.CVSAMaintenanceEvent"
    for event in kafka_mgr.events:
        headers = dict(map(lambda x: (x[0], x[1]), event.headers))
        event_type = headers["ce_type"]
        if bytes(event_type_maintenance, "utf-8") in event_type:
            if event.value["action"] == 1:
                in_maintenance = True

        if in_maintenance:
            events_during_maintenance.append(event)

        if bytes(event_type_maintenance, "utf-8") in event_type:
            if event.value["action"] == 2:
                in_maintenance = False

    return events_during_maintenance


def events_include_type(events: List[Message], event_types: List[str]) -> bool:
    for event in events:
        headers = dict(map(lambda x: (x[0], x[1]), event.headers))
        event_type = headers["ce_type"]
        if str(event_type) in event_types:
            return True
    return False


def verify_events_during_maintenance(kafka_mgr: KafkaManager):
    verify_terminated_event(kafka_mgr, TerminateReason.MAINTENANCE)
    verify_created_event_backup(kafka_mgr, data_protected_gb=None, verify_protected_asset=None)
