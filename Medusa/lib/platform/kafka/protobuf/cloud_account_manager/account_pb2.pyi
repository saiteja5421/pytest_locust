from google.protobuf import timestamp_pb2 as _timestamp_pb2
from .... import validate_pb2 as _validate_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CspAccountInfo(_message.Message):
    __slots__ = ["id", "name", "service_provider_id", "status", "type", "paused", "validation_status", "generation"]
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        STATUS_UNSPECIFIED: _ClassVar[CspAccountInfo.Status]
        STATUS_REGISTERED: _ClassVar[CspAccountInfo.Status]
        STATUS_UNREGISTERED: _ClassVar[CspAccountInfo.Status]
        STATUS_UNREGISTERING: _ClassVar[CspAccountInfo.Status]
    STATUS_UNSPECIFIED: CspAccountInfo.Status
    STATUS_REGISTERED: CspAccountInfo.Status
    STATUS_UNREGISTERED: CspAccountInfo.Status
    STATUS_UNREGISTERING: CspAccountInfo.Status
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        TYPE_UNSPECIFIED: _ClassVar[CspAccountInfo.Type]
        TYPE_AWS: _ClassVar[CspAccountInfo.Type]
        TYPE_AZURE: _ClassVar[CspAccountInfo.Type]
        TYPE_MS365: _ClassVar[CspAccountInfo.Type]
    TYPE_UNSPECIFIED: CspAccountInfo.Type
    TYPE_AWS: CspAccountInfo.Type
    TYPE_AZURE: CspAccountInfo.Type
    TYPE_MS365: CspAccountInfo.Type
    class ValidationStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        VALIDATION_STATUS_UNSPECIFIED: _ClassVar[CspAccountInfo.ValidationStatus]
        VALIDATION_STATUS_UNVALIDATED: _ClassVar[CspAccountInfo.ValidationStatus]
        VALIDATION_STATUS_PASSED: _ClassVar[CspAccountInfo.ValidationStatus]
        VALIDATION_STATUS_FAILED: _ClassVar[CspAccountInfo.ValidationStatus]
    VALIDATION_STATUS_UNSPECIFIED: CspAccountInfo.ValidationStatus
    VALIDATION_STATUS_UNVALIDATED: CspAccountInfo.ValidationStatus
    VALIDATION_STATUS_PASSED: CspAccountInfo.ValidationStatus
    VALIDATION_STATUS_FAILED: CspAccountInfo.ValidationStatus
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SERVICE_PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PAUSED_FIELD_NUMBER: _ClassVar[int]
    VALIDATION_STATUS_FIELD_NUMBER: _ClassVar[int]
    GENERATION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    service_provider_id: str
    status: CspAccountInfo.Status
    type: CspAccountInfo.Type
    paused: bool
    validation_status: CspAccountInfo.ValidationStatus
    generation: int
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., service_provider_id: _Optional[str] = ..., status: _Optional[_Union[CspAccountInfo.Status, str]] = ..., type: _Optional[_Union[CspAccountInfo.Type, str]] = ..., paused: bool = ..., validation_status: _Optional[_Union[CspAccountInfo.ValidationStatus, str]] = ..., generation: _Optional[int] = ...) -> None: ...

class AccountSyncInfo(_message.Message):
    __slots__ = ["account_id", "asset_category", "last_synced_at", "last_sync_status"]
    class AssetCategory(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        ASSET_CATEGORY_UNSPECIFIED: _ClassVar[AccountSyncInfo.AssetCategory]
        ASSET_CATEGORY_MACHINE_INSTANCE_AND_VOLUME: _ClassVar[AccountSyncInfo.AssetCategory]
        ASSET_CATEGORY_DATABASE: _ClassVar[AccountSyncInfo.AssetCategory]
        ASSET_CATEGORY_KUBERNETES: _ClassVar[AccountSyncInfo.AssetCategory]
    ASSET_CATEGORY_UNSPECIFIED: AccountSyncInfo.AssetCategory
    ASSET_CATEGORY_MACHINE_INSTANCE_AND_VOLUME: AccountSyncInfo.AssetCategory
    ASSET_CATEGORY_DATABASE: AccountSyncInfo.AssetCategory
    ASSET_CATEGORY_KUBERNETES: AccountSyncInfo.AssetCategory
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        STATUS_UNSPECIFIED: _ClassVar[AccountSyncInfo.Status]
        STATUS_OK: _ClassVar[AccountSyncInfo.Status]
        STATUS_WARNING: _ClassVar[AccountSyncInfo.Status]
        STATUS_ERROR: _ClassVar[AccountSyncInfo.Status]
        STATUS_UNKNOWN: _ClassVar[AccountSyncInfo.Status]
    STATUS_UNSPECIFIED: AccountSyncInfo.Status
    STATUS_OK: AccountSyncInfo.Status
    STATUS_WARNING: AccountSyncInfo.Status
    STATUS_ERROR: AccountSyncInfo.Status
    STATUS_UNKNOWN: AccountSyncInfo.Status
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ASSET_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNC_STATUS_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    asset_category: AccountSyncInfo.AssetCategory
    last_synced_at: _timestamp_pb2.Timestamp
    last_sync_status: AccountSyncInfo.Status
    def __init__(self, account_id: _Optional[str] = ..., asset_category: _Optional[_Union[AccountSyncInfo.AssetCategory, str]] = ..., last_synced_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., last_sync_status: _Optional[_Union[AccountSyncInfo.Status, str]] = ...) -> None: ...
