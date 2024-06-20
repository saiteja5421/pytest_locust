"""
TC67: Terminate orphaned instance
"""

from pytest import mark

from lib.common.enums.cvsa import StopReason, TerminateReason
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_terminated
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    verify_stopped_event,
    verify_terminated_event,
    create_new_cvsa_instance_and_validate,
)


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
def test_tc67(kafka_mgr: KafkaManager, aws: CloudVmManager):
    create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)

    # ce_forcemissinginstore forces cVSA Manager to ignore the instance from the PSQL results.
    # Expectation is that DesiredState workflow will notice there is an instance in the Cloud, which doesn't exist
    # in the internal model of the service. DesiredState triggers the deletion of resources after some delay,
    # however for the integration tests the delay is set to a few seconds, therefore we expect the stopped
    # and terminated events in the near future.
    tag = Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)
    cloud_instance_id = aws.list_instances(tags=[tag])[0].id
    aws.set_instance_tag(cloud_instance_id, "cvsa-terminate-confirmation", "true")
    send_backup_requested_event(
        kafka_mgr, data_protected_gb=1, headers={"ce_forcemissinginstore": bytes(cloud_instance_id, "utf-8")}
    )
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)

    verify_stopped_event(kafka_mgr, reason=StopReason.ORPHANED)
    verify_terminated_event(kafka_mgr, reason=TerminateReason.ORPHANED)
    verify_instance_terminated(aws, cloud_instance_id)
