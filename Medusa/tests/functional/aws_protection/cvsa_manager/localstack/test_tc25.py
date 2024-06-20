"""
TC25: Deploy cVSA instance on not supported region
    1. Verify that customer has not yet deployed cVSA or remove it.
    2. Send cVSARequestedEvent with not supported region (from Backup Service, or e2e Test suite QA - kafka client)
    3. Check error message
    4. Check EBS, EC2, S3 instances
"""

from pytest import mark

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.cvsa import AwsRegions
from lib.common.enums.cvsa import RequestFinishedStatus
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_not_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_finished_event,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc25(kafka_mgr: KafkaManager, aws: CloudVmManager):
    send_backup_requested_event(kafka_mgr, data_protected_gb=2001, cloud_region=AwsRegions.AWS_ME_SOUTH_1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=2001, cloud_region=AwsRegions.AWS_ME_SOUTH_1)
    verify_finished_event(
        kafka_mgr,
        cloud_region=AwsRegions.AWS_ME_SOUTH_1,
        result=RequestFinishedStatus.STATUS_ERROR,
        error_msg=f"region={AWSRegionZone.ME_SOUTH_1.value} is not allowed",
    )
    verify_not_deployed_cvsa(cloud_vm_mgr=aws, account_id=kafka_mgr.account_id)
