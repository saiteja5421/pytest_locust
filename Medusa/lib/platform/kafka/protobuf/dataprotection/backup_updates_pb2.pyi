from .... import validate_pb2 as _validate_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

ASSET_TYPE_MACHINE_INSTANCE: AssetType
ASSET_TYPE_RDS_DATABASE_INSTANCE: AssetType
ASSET_TYPE_UNSPECIFIED: AssetType
ASSET_TYPE_VOLUME: AssetType
BACKUP_TYPE_BACKUP: BackupType
BACKUP_TYPE_CLOUDBACKUP: BackupType
BACKUP_TYPE_TRANSIENT_BACKUP: BackupType
BACKUP_TYPE_UNSPECIFIED: BackupType
DESCRIPTOR: _descriptor.FileDescriptor
EVENT_STATUS_FAILURE: EventStatus
EVENT_STATUS_SUCCESS: EventStatus
EVENT_STATUS_UNSPECIFIED: EventStatus

class AssetInfo(_message.Message):
    __slots__ = ["id", "type"]
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: AssetType
    def __init__(self, id: _Optional[str] = ..., type: _Optional[_Union[AssetType, str]] = ...) -> None: ...

class BackupCreationInfo(_message.Message):
    __slots__ = ["asset_info", "backup_info", "event_info", "protection_job_info"]
    ASSET_INFO_FIELD_NUMBER: _ClassVar[int]
    BACKUP_INFO_FIELD_NUMBER: _ClassVar[int]
    EVENT_INFO_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_JOB_INFO_FIELD_NUMBER: _ClassVar[int]
    asset_info: AssetInfo
    backup_info: BackupInfo
    event_info: EventInfo
    protection_job_info: ProtectionJobInfo
    def __init__(self, backup_info: _Optional[_Union[BackupInfo, _Mapping]] = ..., asset_info: _Optional[_Union[AssetInfo, _Mapping]] = ..., protection_job_info: _Optional[_Union[ProtectionJobInfo, _Mapping]] = ..., event_info: _Optional[_Union[EventInfo, _Mapping]] = ...) -> None: ...

class BackupDeletionInfo(_message.Message):
    __slots__ = ["asset_info", "backup_info"]
    ASSET_INFO_FIELD_NUMBER: _ClassVar[int]
    BACKUP_INFO_FIELD_NUMBER: _ClassVar[int]
    asset_info: AssetInfo
    backup_info: BackupInfo
    def __init__(self, backup_info: _Optional[_Union[BackupInfo, _Mapping]] = ..., asset_info: _Optional[_Union[AssetInfo, _Mapping]] = ...) -> None: ...

class BackupInfo(_message.Message):
    __slots__ = ["id", "type"]
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: BackupType
    def __init__(self, id: _Optional[str] = ..., type: _Optional[_Union[BackupType, str]] = ...) -> None: ...

class EventInfo(_message.Message):
    __slots__ = ["status", "time"]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    status: EventStatus
    time: _timestamp_pb2.Timestamp
    def __init__(self, status: _Optional[_Union[EventStatus, str]] = ..., time: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ProtectionGroupBackupResult(_message.Message):
    __slots__ = ["event_info", "protection_group_id", "protection_job_info"]
    EVENT_INFO_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_GROUP_ID_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_JOB_INFO_FIELD_NUMBER: _ClassVar[int]
    event_info: EventInfo
    protection_group_id: str
    protection_job_info: ProtectionJobInfo
    def __init__(self, protection_group_id: _Optional[str] = ..., protection_job_info: _Optional[_Union[ProtectionJobInfo, _Mapping]] = ..., event_info: _Optional[_Union[EventInfo, _Mapping]] = ...) -> None: ...

class ProtectionJobInfo(_message.Message):
    __slots__ = ["id", "schedule_id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    SCHEDULE_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    schedule_id: int
    def __init__(self, id: _Optional[str] = ..., schedule_id: _Optional[int] = ...) -> None: ...

class BackupType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class AssetType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class EventStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
