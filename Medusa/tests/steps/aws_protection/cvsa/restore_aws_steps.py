import logging

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import CloudProvider
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_allowed_instances import get_instance_details_by_name, is_allowed
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import allocated_by_tag

logger = logging.getLogger()


def verify_restore_cvsa(
    cloud_vm_mgr: CloudVmManager, kafka: KafkaManager, cvsa_id: str, instance_details=CloudInstanceDetails.R6I_LARGE
):
    logger.info("Start verifying restore cvsa")
    logger.info(f"Searching instances, cvsa-id: {cvsa_id}")
    tag = Tag(Key="cvsa-id", Value=cvsa_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag])
    logger.info(f"Found instances: {instances}")
    assert len(instances) == 1

    instance = instances[0]
    volume = instance.data_disks[0]
    instance_tags = instance.tags
    instance_subnets = instance.subnets

    assert instance.state == CloudInstanceState.RUNNING
    assert Tag(Key="cvsa-application-customer-id", Value=kafka.account_id) in instance_tags
    assert Tag(Key="cvsa-cloud-account-manager-account-id", Value=kafka.cam_account_id) in instance_tags
    assert Tag(Key="cvsa-cloud-service-provider-account-id", Value=kafka.csp_account_id) in instance_tags

    instance_type = instance_details.value.instance_type
    logger.info("Start verifying instance type")
    cloud_instance_type = instance.instance_type
    if instance_type == cloud_instance_type:
        assert instance_type == cloud_instance_type, f"expected: {instance_type}, actual: {cloud_instance_type}"
    else:
        logger.error(
            f"Given instance type not match requested instance type. Given: {instance_type},"
            f" Requested: {cloud_instance_type}"
        )
        given_instance = get_instance_details_by_name(instance_type)
        assert is_allowed(
            instance_details, given_instance
        ), f"Instance is to big, wanted: {instance_details}, given: {given_instance}"
    logger.info("Instance type verified")

    logger.info(f"Starting volume verification: {volume}")
    assert volume is not None
    assert volume.state == "attached"
    assert volume.instance_id == instance.id
    assert tag in volume.tags
    logger.info(f"Finished volume verification: {volume}")

    logger.info(f"Found subnets: {instance_subnets}")
    assert len(instance_subnets) == 1
    if instance.cloud_provider == CloudProvider.AWS:
        assert allocated_by_tag() in instance_subnets[0].tags
    logger.info(f"Finished subnet verification: {instance_subnets}")
    logger.info("Finished restore cvsa verification")
