from .... import validate_pb2 as _validate_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CspAccountUseByService(_message.Message):
    __slots__ = ["account_id", "service_name", "is_in_use"]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    SERVICE_NAME_FIELD_NUMBER: _ClassVar[int]
    IS_IN_USE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    service_name: str
    is_in_use: bool
    def __init__(self, account_id: _Optional[str] = ..., service_name: _Optional[str] = ..., is_in_use: bool = ...) -> None: ...
