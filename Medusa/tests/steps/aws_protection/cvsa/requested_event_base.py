import lib.platform.kafka.protobuf.cvsa_manager.cvsa_manager_pb2 as cvsa_manager_pb2
from lib.common.enums.cvsa import CloudProvider, CloudRegions
from lib.platform.kafka.kafka_manager import KafkaManager


def set_requested_event_base(
    kafka_manager: KafkaManager,
    event: cvsa_manager_pb2,
    cloud_region: CloudRegions,
    cloud_provider: CloudProvider = CloudProvider.AWS,
) -> None:
    if cloud_provider == CloudProvider.AWS:
        event.base.cloud_provider = cvsa_manager_pb2.CLOUD_PROVIDER_ENUM_AWS
    else:
        event.base.cloud_provider = cvsa_manager_pb2.CLOUD_PROVIDER_ENUM_AZURE
    event.base.cloud_region = cloud_region.value
    event.base.protected_asset_type = cvsa_manager_pb2.PROTECTED_ASSET_TYPE_ENUM_AWS_EBS
    event.base.correlation_id = kafka_manager.correlation_id.decode("utf-8")
    event.base.csp_account_id = kafka_manager.csp_account_id.decode("utf-8")
    event.base.cam_account_id = kafka_manager.cam_account_id.decode("utf-8")
