"""
TC27: Disaster Recovery verification
    1. Create new cVSA instance (unconfigured due to forced behavior)
    2. Terminate cloud instance and verify that Disaster Recovery is not triggered to unconfigured instance
    3. Send another backup request in order to finish the instance configuration
    4. Create additional orphan instance which may potentially affect the normal cVSA
    5. Trigger the Disaster Recovery
    6. Check if created orphan cloud instance was terminated,
        Confirm there are no instances which could interfere with the attempted Disaster Recovery,
    7. Wait until Disaster Recovery is finished,
        Verify expected maintenance events for Disaster Recovery,
    8. Check if only one valid cVSA exists after Disaster Recovery,
    9. Verify cVSA resources,
"""

import time

from pytest import mark

from lib.common.enums.cvsa import MaintenanceAction, MaintenanceOperation, TerminateReason, RequestFinishedStatus
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.assertions import assert_one_cvsa_running
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    create_orphaned_instance,
    verify_instance_running,
    verify_instance_terminated,
    verify_deployed_cvsa,
    get_data_volume,
    verify_volume_deleted,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
    verify_instance_type_and_volume_size,
    verify_started_event,
    verify_created_event_backup,
    verify_terminated_event,
)
from tests.steps.aws_protection.cvsa.kafka_steps import (
    verify_maintenance_event,
    verify_no_maintenance_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc27(kafka_mgr: KafkaManager, aws: CloudVmManager):
    # 1. Create unconfigured cVSA instance
    send_backup_requested_event(
        kafka_mgr,
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

    # 2. Terminate cloud instance
    unconfigured_instance_id = aws.list_instances(
        tags=[
            Tag(
                Key="cvsa-cloud-service-provider-account-id",
                Value=kafka_mgr.csp_account_id,
            )
        ]
    )[0].id
    aws.terminate_instance(unconfigured_instance_id)

    # 3. Verify that DR is not triggered
    verify_no_maintenance_event(kafka_mgr, timeout=300)

    # 4.Finish instance configuration
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1, verify_not_deployed=False
    )
    data_volume = get_data_volume(aws, kafka_mgr.cvsa_id)

    # 5. Create orphan instance which may potentially affect the normal cVSA.
    cloud_instance_id = aws.list_instances(
        tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)],
        states=CloudInstanceState.list_not_terminated(),
    )[0].id
    orphaned_instance = create_orphaned_instance(kafka_mgr, aws)
    verify_instance_running(aws, orphaned_instance.id)

    # 6. Trigger the Disaster Recovery
    aws.terminate_instance(cloud_instance_id)
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )

    # 7. Check if created orphan cloud instance was terminated
    verify_terminated_event(kafka_mgr, reason=TerminateReason.MAINTENANCE, cloud_instance_id=orphaned_instance.id)
    verify_instance_terminated(aws, orphaned_instance.id)

    # 8. Verify maintenance events for Disaster Recovery.
    verify_created_event_backup(kafka_mgr, data_protected_gb=None, verify_protected_asset=None)
    verify_started_event(kafka=kafka_mgr, timeout=Timeout.STARTED_EVENT_DURING_MAINTENANCE.value)
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )

    # 9. Check if orphaned volume was deleted
    verify_volume_deleted(aws, data_volume.name)

    # 10. Assert if only one valid instance exists in the customer account region scope, after Disaster Recovery is finished.
    assert_one_cvsa_running(kafka_mgr=kafka_mgr, cloud_vm_mgr=aws)

    # 11. Verify the recovered cVSA.
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id, disaster_recovery=True)
    verify_instance_type_and_volume_size(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
