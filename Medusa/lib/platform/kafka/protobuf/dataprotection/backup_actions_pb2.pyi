from .... import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class InitiateBackupRequest(_message.Message):
    __slots__ = ["headers", "payload", "payload_mime_type", "trigger_type"]
    class TriggerType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    class HeadersEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_TYPE_ONDEMAND: InitiateBackupRequest.TriggerType
    TRIGGER_TYPE_SCHEDULED: InitiateBackupRequest.TriggerType
    TRIGGER_TYPE_UNSPECIFIED: InitiateBackupRequest.TriggerType
    headers: _containers.ScalarMap[str, str]
    payload: bytes
    payload_mime_type: str
    trigger_type: InitiateBackupRequest.TriggerType
    def __init__(self, headers: _Optional[_Mapping[str, str]] = ..., trigger_type: _Optional[_Union[InitiateBackupRequest.TriggerType, str]] = ..., payload_mime_type: _Optional[str] = ..., payload: _Optional[bytes] = ...) -> None: ...

class NightlyTrigger(_message.Message):
    __slots__ = ["account_id", "csp_region"]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    CSP_REGION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    csp_region: str
    def __init__(self, account_id: _Optional[str] = ..., csp_region: _Optional[str] = ...) -> None: ...
