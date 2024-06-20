"""
TC-57: Restore request for instance with large data protected recovered bytes
"""

import logging

from pytest import fixture, mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_main_cvsa_instance,
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events


@fixture(scope="function")
def kafka_mgr(aws: CloudVmManager):
    kafka_mgr = new_kafka_lifecycle_events(tc_id=57)
    yield kafka_mgr
    logger = logging.getLogger()
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(kafka_mgr, aws)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc57(kafka_mgr, aws: CloudVmManager):
    # Create backup cVSA and finish backup request.
    create_main_cvsa_instance(kafka_mgr, aws)
    # Create restore cVSA for 20 TBs.
    create_read_only_replica(
        kafka_mgr, recovery_gigabytes=20_000, instance_details=CloudInstanceDetails.C6I_16XLARGE, restore_streams=20
    )
