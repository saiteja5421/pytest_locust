from enum import Enum

import lib.platform.kafka.protobuf.inventory_manager.asset_pb2 as asset


class KafkaInventoryAssetType(Enum):
    # Used for Backup Kafka Event
    ASSET_TYPE_MACHINE_INSTANCE = asset.AssetType.DESCRIPTOR.values_by_number[asset.ASSET_TYPE_MACHINE_INSTANCE].name
    ASSET_TYPE_VOLUME = asset.AssetType.DESCRIPTOR.values_by_number[asset.ASSET_TYPE_VOLUME].name
