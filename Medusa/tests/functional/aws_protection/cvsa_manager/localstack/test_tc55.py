"""
TC-55: Unregister customer when restore (read only replica) is in progress
"""

from pytest import mark, fixture

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_main_cvsa_instance,
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events


@fixture(scope="function")
def kafka_mgr(aws: CloudVmManager):
    kafka_mgr = new_kafka_lifecycle_events(tc_id=55)
    yield kafka_mgr


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc55(kafka_mgr, aws: CloudVmManager):
    # Create backup cVSA and finish backup request.
    create_main_cvsa_instance(kafka_mgr, aws)
    # Create restore cVSA and leave it pending.
    create_read_only_replica(kafka_mgr)
    # Unregister (while restore is in progress)
    cleanup_cvsa_instance(kafka_mgr, aws)
