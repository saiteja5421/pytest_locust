from google.protobuf import timestamp_pb2 as _timestamp_pb2
from .. import validate_pb2 as _validate_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class AccountSyncInfo(_message.Message):
    __slots__ = ["account_id", "last_sync_status", "last_synced_at"]

    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNCED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_SYNC_STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_ERROR: AccountSyncInfo.Status
    STATUS_OK: AccountSyncInfo.Status
    STATUS_UNKNOWN: AccountSyncInfo.Status
    STATUS_UNSPECIFIED: AccountSyncInfo.Status
    STATUS_WARNING: AccountSyncInfo.Status
    account_id: str
    last_sync_status: AccountSyncInfo.Status
    last_synced_at: _timestamp_pb2.Timestamp
    def __init__(
        self,
        account_id: _Optional[str] = ...,
        last_synced_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...,
        last_sync_status: _Optional[_Union[AccountSyncInfo.Status, str]] = ...,
    ) -> None: ...

class SyncAccountRequest(_message.Message):
    __slots__ = ["account_id", "service_id"]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_ID_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    service_id: str
    def __init__(self, service_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...
