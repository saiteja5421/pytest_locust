from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import CloudProvider
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_models import CvsaEvent
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.cloud_steps import get_default_instance, get_default_region

from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    create_new_cvsa_instance_and_validate,
)

from tests.steps.aws_protection.cvsa.restore_kafka_steps import (
    send_restore_requested_event,
    verify_restore_requested_event,
    verify_restore_created_event,
    verify_restore_ready_event,
)


def create_main_cvsa_instance(kafka_mgr: KafkaManager, aws: CloudVmManager) -> CvsaEvent:
    cvsa_model = create_new_cvsa_instance_and_validate(cloud_vm_mgr=aws, kafka_mgr=kafka_mgr, data_protected_gb=1)
    send_finished_event(kafka_mgr)
    return cvsa_model


def create_read_only_replica(
    kafka_mgr: KafkaManager,
    recovery_gigabytes: int = 1,
    instance_details: CloudInstanceDetails = None,
    restore_streams: int = 8,
    cloud_provider: CloudProvider = CloudProvider.AWS,
) -> CvsaEvent:
    if instance_details is None:
        instance_details = get_default_instance(cloud_provider=cloud_provider)
    cloud_region = get_default_region(cloud_provider=cloud_provider)
    send_restore_requested_event(
        kafka_mgr, recovery_gigabytes, cloud_region=cloud_region, cloud_provider=cloud_provider
    )
    verify_restore_requested_event(
        kafka_mgr, recovery_gigabytes, cloud_region=cloud_region, cloud_provider=cloud_provider
    )
    verify_restore_created_event(
        kafka_mgr,
        instance_details=instance_details,
        restore_streams=restore_streams,
        cloud_region=cloud_region,
        cloud_provider=cloud_provider,
    )
    return verify_restore_ready_event(
        kafka_mgr,
        instance_details=instance_details,
        restore_streams=restore_streams,
        cloud_region=cloud_region,
        cloud_provider=cloud_provider,
    )
