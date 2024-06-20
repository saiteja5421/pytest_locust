from . import asset_pb2 as _asset_pb2
from .. import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class GetProtectionGroupRequest(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class GetProtectionGroupResponse(_message.Message):
    __slots__ = ["protection_group"]
    PROTECTION_GROUP_FIELD_NUMBER: _ClassVar[int]
    protection_group: ProtectionGroupDetails
    def __init__(
        self,
        protection_group: _Optional[_Union[ProtectionGroupDetails, _Mapping]] = ...,
    ) -> None: ...

class ProtectionGroupDetails(_message.Message):
    __slots__ = ["payload", "payload_mime_type"]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    payload: bytes
    payload_mime_type: str
    def __init__(self, payload_mime_type: _Optional[str] = ..., payload: _Optional[bytes] = ...) -> None: ...

class ResolveProtectionGroupRequest(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ResolveProtectionGroupResponse(_message.Message):
    __slots__ = ["assets", "protection_group"]
    ASSETS_FIELD_NUMBER: _ClassVar[int]
    PROTECTION_GROUP_FIELD_NUMBER: _ClassVar[int]
    assets: _containers.RepeatedCompositeFieldContainer[_asset_pb2.AssetDetails]
    protection_group: ProtectionGroupDetails
    def __init__(
        self,
        protection_group: _Optional[_Union[ProtectionGroupDetails, _Mapping]] = ...,
        assets: _Optional[_Iterable[_Union[_asset_pb2.AssetDetails, _Mapping]]] = ...,
    ) -> None: ...
