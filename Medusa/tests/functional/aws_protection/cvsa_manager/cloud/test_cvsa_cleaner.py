"""
cVSA Cleaner - clean up resources on environment
"""

import logging

from pytest import fixture, mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.cloud_steps import get_creator_environment_name, get_default_region
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events
from utils.cvsa_cleaner import cvsa_full_cleanup

logger = logging.getLogger()


@fixture(scope="function")
def kafka_mgr():
    # Kafka Manager is required for logging
    kafka_mgr = new_kafka_lifecycle_events(tc_id=0)
    yield kafka_mgr


@mark.cvsa_aws
@mark.cvsa_azure
@mark.cvsa_cloud
@mark.cvsa_azure_master
@mark.cvsa_aws_master
@mark.cvsa_cloud_master
@mark.parametrize("cloud_vm_mgr", ["azure", "aws"])
def test_cloud_cleaner(cloud_vm_mgr: CloudVmManager, request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)
    env = get_creator_environment_name()
    region = get_default_region(cloud_vm_mgr.name())
    if env:
        cvsa_full_cleanup(region, env, cloud_vm_mgr=cloud_vm_mgr)
    else:
        logger.error(f"CREATOR_ENVIRONMENT_NAME or {cloud_vm_mgr.name().name}_REGION_ONE env variable is not set")
        logger.error(f"CREATOR_ENVIRONMENT_NAME: {env}, CLOUD_REGION: {region}")
