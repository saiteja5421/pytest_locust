"""
TC05: UPSCALE. Backup/restore request when cVSA Instance need resize. Calculating EBS Volume Size.
    1. Verify that EBS size and cloudbank.
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA)
    2. Check cVSAStoppedEvent
    3. Check cVSAStartedEvent  (to ensure that instance is running, happens always)
    5. Check cVSAResizedEvent
    6. Check cVSAReadyEvent
    7. Verify that EBS size was changed
TC06: UPSCALE. Backup/restore request when cVSA Instance need resize. Check if compute (CPU&RAM) resized. Calculate EC2 type.
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
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import USER_BYTES_EXPECTED
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_resize_event,
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    verify_instance_type_and_volume_size,
    verify_stopped_event,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.storeonce_steps import (
    verify_cloud_stores,
    verify_storeonce_system,
    validate_cloud_store_data,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials
from tests.steps.aws_protection.cvsa.write_read_backup_steps import write_data_to_cvsa_cloud_store


@mark.order(500)
@mark.cvsa_aws
@mark.cvsa_cloud
@mark.parametrize(
    "prev_protected_data_gb, protected_data_gb, instance_details, backup_streams, volume_size_bytes, user_bytes_expected",
    [
        (10, 30000, CloudInstanceDetails.C6I_12XLARGE, 10, 340_247_671_987, USER_BYTES_EXPECTED),
    ],
)
def test_tc06(
    kafka_mgr: KafkaManager,
    aws: CloudVmManager,
    prev_protected_data_gb,
    protected_data_gb,
    instance_details,
    backup_streams,
    volume_size_bytes,
    user_bytes_expected,
):
    cvsa_model = create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=10)
    verify_cloud_stores(cloud_vm_mgr=aws, kafka=kafka_mgr, cloud_bank_name=cvsa_model.catalyst_store)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_storeonce_system(kafka_mgr, aws)
    write_data_to_cvsa_cloud_store(aws, kafka_mgr, cvsa_model.catalyst_store)
    validate_cloud_store_data(aws, kafka_mgr)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    send_backup_requested_event(kafka_mgr, protected_data_gb, prev_protected_data_gb)
    verify_backup_requested_event(kafka_mgr, protected_data_gb)
    verify_stopped_event(kafka_mgr)
    verify_started_event(kafka_mgr)
    verify_resize_event(kafka_mgr, protected_data_gb, instance_details, backup_streams, volume_size_bytes)
    verify_ready_event(kafka_mgr, instance_details, backup_streams, volume_size_bytes)
    verify_cloud_stores(cloud_vm_mgr=aws, kafka=kafka_mgr, cloud_bank_name=cvsa_model.catalyst_store)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
    )
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
    validate_cloud_store_data(aws, kafka_mgr)
    verify_storeonce_system(kafka_mgr, aws, volume_size_bytes, user_bytes_expected)
