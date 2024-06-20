from dataclasses import dataclass, field
import json
from typing import List, Optional
from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DataVolume:
    size_bytes: int
    type: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudResources:
    compute_type: str
    cpu: int
    ram: int
    data_volume: DataVolume
    backup_streams: Optional[int] = None
    restore_streams: Optional[int] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectedData:
    backup_window_hours: int
    protected_asset_type: int
    data_protected_bytes: str = field(default=0)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CvsaEvent:
    headers: List[tuple[str]]
    cvsa_id: str
    cloud_provider: int
    cloud_region: int
    address: str
    cloud_resources: CloudResources
    cam_account_id: str = field(default="")
    protected_data: ProtectedData = field(default=ProtectedData(0, 0, ""))
    catalyst_store: str = field(default="")
    correlation_id: str = field(default="")

    @staticmethod
    def from_message(kafka_message):
        event_data = kafka_message.value.copy()
        event_data["headers"] = [(v[0], v[1].decode("utf-8")) for v in kafka_message.headers]
        event_json = json.dumps(event_data).encode("utf-8")
        return CvsaEvent.from_json(event_json)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStore:
    cloud_store_id: str
    cloud_store_name: str
    region: str
    cloud_user_bytes: int
    cloud_disk_bytes: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionStoreUtilizationUpdate:
    app_type: str
    account_id: str
    csp_id: str
    catalyst_gateway_id: str
    catalyst_gateway_name: str
    cloud_stores: list[CloudStore]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionStoreDelete:
    app_type: str
    account_id: str
    csp_id: str
    catalyst_gateway_id: str
    cloud_store_id: str
    cloud_store_name: str
