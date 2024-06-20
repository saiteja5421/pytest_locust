"""
TC06: Backup/restore request when cVSA Instance need resize. Check if compute (CPU&RAM) resized. Calculate EC2 type.
    Upscale and Downscale of EC2 instance
    1. Verify EBS size and cloudbank.
    2. Verify CPU & RAM resources
    3. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA)
    4. Check cVSAStoppedEvent
    5. Check cVSAStartedEvent  (to ensure that instance is running, happens always)
    6. Check cVSAResizedEvent
    7. Check cVSAReadyEvent
    8. Verify CPU & RAM resources decrease/increase.
    9. Verify that EC2 is a different type.
"""

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_resize_event,
    verify_instance_type_and_volume_size,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc06(kafka_mgr, aws: CloudVmManager):
    # Create base instance r6i.large.
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    # Upscale the instance to m6i.xlarge.
    verify_instance_scaling(
        kafka_mgr,
        aws,
        data_protected_gb=2000,
        data_protected_previous_gb=1,
        expected_instance_details=CloudInstanceDetails.M6I_XLARGE,
    )

    # Downscale the instance back to r6i.large.
    verify_instance_scaling(
        kafka_mgr,
        aws,
        data_protected_gb=1,
        data_protected_previous_gb=2000,
        expected_instance_details=CloudInstanceDetails.R6I_LARGE,
    )


def verify_instance_scaling(
    kafka_mgr,
    aws,
    data_protected_gb: int,
    data_protected_previous_gb: int,
    expected_instance_details: CloudInstanceDetails,
):
    send_backup_requested_event(
        kafka_mgr, data_protected_gb=data_protected_gb, data_protected_previous_gb=data_protected_previous_gb
    )
    verify_resize_event(
        kafka_mgr,
        data_protected_gb=data_protected_gb,
        instance_details=expected_instance_details,
        strict_instance_details=True,
    )
    verify_ready_event(kafka_mgr, instance_details=expected_instance_details, strict_instance_details=True)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=expected_instance_details,
        strict_instance_details=True,
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
