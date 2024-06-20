"""
TC02: Backup and restore request with different protected size when cVSA instance is properly sized and running.
    1. Verify that cVSA is running
    2. Check 2nd parallel backup before 1st backup is end
    3. Check cVSAStartedEvent  (to ensure that instance is running, happens always)
    4. Check cVSAReadyEvent (At this point cVSA is ready to serve the request)
    5. Validate :
     - Cloud compute resource created.
     - Subnet is properly chosen by tag
    6. Verify that cVSA is running and ready
    7. Send restore request when cVSA instance is running and processing backup request
    8. Finish 2nd backup
"""
import copy
import logging

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import CvsaType, RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_type_and_volume_size, verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_created_event,
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
)
from tests.steps.aws_protection.cvsa.restore_aws_steps import verify_restore_cvsa
from tests.steps.aws_protection.cvsa.restore_kafka_steps import verify_restore_ready_event
from tests.steps.aws_protection.cvsa.restore_request_steps import (
    send_restore_requested_event,
    verify_restore_requested_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials

logger = logging.getLogger()


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc02(kafka_mgr: KafkaManager, aws: CloudVmManager):
    logging.info("Step 1. Sending first backup")
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    first_kafka_mgr = copy.copy(kafka_mgr)

    logger.info("Step 1.1 Check 2nd backup before first backup is end")
    send_backup_requested_event(kafka_mgr, data_protected_gb=1, data_protected_previous_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1, data_protected_previous_gb=1)
    verify_finished_event(
        kafka_mgr,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg="parallel backup/backup cvsa requested events not allowed",
    )

    logger.info("Step 1.2 Finish first backup")
    send_finished_event(first_kafka_mgr)
    verify_finished_event(first_kafka_mgr)

    logger.info("Step 2. Sending second backup")
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    verify_ready_event(kafka_mgr)

    logger.info("Step 3. Verify cvsa, its type and ebs size")
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=CloudInstanceDetails.M6I_XLARGE,
    )
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)

    logger.info("Step 4. Send restore during backup")
    backup_kafka_mgr = copy.copy(kafka_mgr)
    send_restore_requested_event(kafka_mgr, data_protected_gb=0)
    verify_restore_requested_event(kafka_mgr, data_protected_gb=None)
    verify_created_event(kafka_mgr, backup_streams=None, restore_streams=8)
    verify_started_event(kafka_mgr)
    restore_cvsa = verify_restore_ready_event(kafka_mgr)
    verify_restore_cvsa(aws, kafka_mgr, restore_cvsa.cvsa_id)
    verify_ready_event(kafka_mgr, restore_streams=8, backup_streams=None)

    logger.info("Step 5. Verify cvsa, its type and ebs size")
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id, cvsa_type=CvsaType.RESTORE)
    verify_instance_type_and_volume_size(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=kafka_mgr.cvsa_id)

    logger.info("Step 5.1 Finish 2nd backup")
    send_finished_event(backup_kafka_mgr)
    verify_finished_event(backup_kafka_mgr)
