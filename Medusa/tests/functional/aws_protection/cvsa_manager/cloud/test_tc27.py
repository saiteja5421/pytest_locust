"""
TC27: Disaster Recovery verification
    1. Create new cVSA instance
    2. Add an artificial orphan created by tests
    3. Trigger the disaster recovery via valid instance termination
    4. Check if created orphan is terminated
        to confirm there are no instances which could interfere with the attempted Disaster Recovery,
    5. Verify events
    6. Confirm if Disaster Recovery was performed correctly
        check if only one valid instance exists in the customer account region scope
    7. Verify instance resources
"""

import logging

from pytest import mark
from pytest_check import check

from lib.common.enums.cvsa import MaintenanceAction, MaintenanceOperation, TerminateReason, CloudProvider
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_timeout_manager import Timeout
from lib.platform.cloud.cloud_vm_manager import CloudVmManager, cloud_vm_managers_names
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import USER_BYTES_EXPECTED
from tests.steps.aws_protection.cvsa.assertions import assert_one_cvsa_running
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import (
    verify_instance_terminated,
    create_orphaned_instance,
    verify_instance_exists,
    verify_deployed_cvsa,
    get_instance_by_cvsa_id,
    get_data_volume,
    verify_volume_deleted,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    create_new_cvsa_instance_and_validate,
    verify_instance_type_and_volume_size,
    verify_started_event,
    verify_created_event_backup,
    verify_terminated_event,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.kafka_steps import verify_maintenance_event
from tests.steps.aws_protection.cvsa.storeonce_steps import validate_cloud_store_data, verify_storeonce_system
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials
from tests.steps.aws_protection.cvsa.write_read_backup_steps import write_data_to_cvsa_cloud_store


@mark.order(4500)
@mark.cvsa_aws
@mark.cvsa_cloud
@mark.parametrize("cloud_vm_mgr", cloud_vm_managers_names())
def test_tc27_cloud(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)

    logging.info("Step 1. Create new cVSA instance.")
    cvsa_model = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=cloud_vm_mgr, kafka_mgr=kafka_mgr, data_protected_gb=1
    )
    data_volume = get_data_volume(cloud_vm_mgr, kafka_mgr.cvsa_id)

    if cloud_vm_mgr.name() == CloudProvider.AWS:
        write_data_to_cvsa_cloud_store(cloud_vm_mgr, kafka_mgr, cvsa_model.catalyst_store)
        validate_cloud_store_data(cloud_vm_mgr, kafka_mgr)

    logging.info("Step 2. Create orphan instance which may potentially affect the normal cVSA.")
    cloud_instance_id = get_instance_by_cvsa_id(cloud_vm_mgr, kafka_mgr.cvsa_id).id
    orphaned_instance = create_orphaned_instance(kafka_mgr, cloud_vm_mgr)
    verify_instance_exists(cloud_vm_mgr, orphaned_instance.id)

    logging.info("Step 3. Trigger the disaster recovery")
    cloud_vm_mgr.terminate_instance(cloud_instance_id)
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.START,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )

    logging.info("Step 4. Check if old resources are cleaned (created orphan is terminated, old volume is deleted)")
    verify_terminated_event(kafka_mgr, reason=TerminateReason.MAINTENANCE, cloud_instance_id=orphaned_instance.id)
    verify_instance_terminated(cloud_vm_mgr, orphaned_instance.id)
    verify_volume_deleted(cloud_vm_mgr, data_volume.name)

    logging.info("Step 5. Verify events")
    verify_created_event_backup(
        kafka_mgr, data_protected_gb=None, verify_protected_asset=None, cloud_provider=cloud_vm_mgr.name()
    )
    verify_started_event(kafka=kafka_mgr, timeout=Timeout.STARTED_EVENT_DURING_MAINTENANCE.value)
    verify_maintenance_event(
        kafka_mgr=kafka_mgr,
        action=MaintenanceAction.STOP,
        operation_type=MaintenanceOperation.DISASTER_RECOVERY,
    )

    logging.info("Step 6. Assert if only one valid instance exists in the customer account region scope")
    assert_one_cvsa_running(kafka_mgr=kafka_mgr, cloud_vm_mgr=cloud_vm_mgr)

    logging.info("Step 7. Verify resources")
    if cloud_vm_mgr.name() == CloudProvider.AZURE:
        user_bytes_expected = 0
    else:
        user_bytes_expected = USER_BYTES_EXPECTED
    with check:
        verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id, disaster_recovery=True)
        verify_instance_type_and_volume_size(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id)
        verify_storeonce_system(kafka_mgr, cloud_vm_mgr, user_bytes_expected=user_bytes_expected)
        if cloud_vm_mgr.name() == CloudProvider.AWS:
            validate_cloud_store_data(cloud_vm_mgr, kafka_mgr)

    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    verify_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())

    if cloud_vm_mgr.name() == CloudProvider.AWS:
        logging.info("Step 8. Check backup after DR")
        send_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=cloud_vm_mgr.name())
        verify_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=cloud_vm_mgr.name())
        verify_started_event(kafka_mgr)
        cvsa_model_dr = verify_ready_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
        verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id, disaster_recovery=True)
        verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)
        write_data_to_cvsa_cloud_store(cloud_vm_mgr, kafka_mgr, cvsa_model_dr.catalyst_store)
        validate_cloud_store_data(cloud_vm_mgr, kafka_mgr)
