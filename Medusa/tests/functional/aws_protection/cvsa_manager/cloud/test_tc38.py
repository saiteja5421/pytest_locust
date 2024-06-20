"""
TC38: Send Restore request right after a finished Backup.
    # Restore request for RO cVSA Replicas
    # Confirm that RO cVSA is terminated after request is finished.
    Send Finished event on running instance
    During Finished workflow, before generating support bundle send restore request.
    Verify cloud stores for RO cVSA replica
    Verify cloud stores for RW cVSA
    Verify that ec2 wasn't stopped
    Verify Started event
    Verify Ready event
"""

from pytest import mark

from lib.common.enums.cvsa import TerminateReason
from lib.platform.cloud.cloud_vm_manager import CloudVmManager, cloud_vm_managers_names
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.assertions import assert_object_store_count
from tests.steps.aws_protection.cvsa.cvsa_manager_restore_steps import (
    create_read_only_replica,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_terminated_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.grpc_steps import is_cosm_enabled


@mark.order(3800)
@mark.cvsa_aws
@mark.cvsa_azure
@mark.cvsa_cloud
@mark.parametrize("cloud_vm_mgr", cloud_vm_managers_names())
def test_tc38(cloud_vm_mgr: CloudVmManager, kafka_mgr_ro_rw: KafkaManager, request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)

    kafka_mgr_rw, kafka_mgr_ro = kafka_mgr_ro_rw
    # Create RW cVSA.
    # In order to perform Restore request, we firstly need to have a finished backup (and have Cloud Store created).
    cvsa_rw = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=cloud_vm_mgr, kafka_mgr=kafka_mgr_rw, data_protected_gb=1
    )
    send_finished_event(kafka_mgr_rw, cloud_provider=cloud_vm_mgr.name())

    # Create RO cVSA Replica.
    cvsa_ro = create_read_only_replica(kafka_mgr_ro, cloud_provider=cloud_vm_mgr.name())
    # Confirm that cVSA ID is different for RO cVSA Replica (i.e. that it's a different cloud instance).
    # Assert that RW and RO instances are different.
    assert cvsa_rw.cvsa_id != cvsa_ro.cvsa_id, f"cVSA for Restore should be different if RO Replicas are enabled"
    if is_cosm_enabled():
        assert_object_store_count(cvsa_id=cvsa_rw.cvsa_id, count=1)
        assert_object_store_count(cvsa_id=cvsa_ro.cvsa_id, count=0)

    # RO cVSA Replica should be terminated after restore request is finished.
    # Lifetime of RO cVSA Replicas are expected to be equal to the lifetime of each particular request.
    send_finished_event(kafka_mgr_ro, cloud_provider=cloud_vm_mgr.name())

    verify_terminated_event(kafka_mgr_ro, TerminateReason.READ_ONLY_REQUEST_FINISHED)
