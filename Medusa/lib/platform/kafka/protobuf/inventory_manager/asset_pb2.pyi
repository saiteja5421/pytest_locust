from .. import validate_pb2 as _validate_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

ACTION_TYPE_CREATED: ActionType
ACTION_TYPE_DELETED: ActionType
ACTION_TYPE_UNSPECIFIED: ActionType
ASSET_TYPE_MACHINE_INSTANCE: AssetType
ASSET_TYPE_UNSPECIFIED: AssetType
ASSET_TYPE_VOLUME: AssetType
DESCRIPTOR: _descriptor.FileDescriptor

class AffectedAsset(_message.Message):
    __slots__ = ["action", "source_id", "type"]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    action: ActionType
    source_id: str
    type: AssetType
    def __init__(
        self,
        type: _Optional[_Union[AssetType, str]] = ...,
        action: _Optional[_Union[ActionType, str]] = ...,
        source_id: _Optional[str] = ...,
    ) -> None: ...

class AssetDetails(_message.Message):
    __slots__ = ["payload", "payload_mime_type", "type"]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    payload: bytes
    payload_mime_type: str
    type: AssetType
    def __init__(
        self,
        type: _Optional[_Union[AssetType, str]] = ...,
        payload_mime_type: _Optional[str] = ...,
        payload: _Optional[bytes] = ...,
    ) -> None: ...

class AssetStateInfo(_message.Message):
    __slots__ = ["id", "state", "type"]

    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ID_FIELD_NUMBER: _ClassVar[int]
    STATE_DELETED: AssetStateInfo.State
    STATE_FIELD_NUMBER: _ClassVar[int]
    STATE_OK: AssetStateInfo.State
    STATE_UNSPECIFIED: AssetStateInfo.State
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    state: AssetStateInfo.State
    type: AssetType
    def __init__(
        self,
        type: _Optional[_Union[AssetType, str]] = ...,
        id: _Optional[str] = ...,
        state: _Optional[_Union[AssetStateInfo.State, str]] = ...,
    ) -> None: ...

class GetAssetRequest(_message.Message):
    __slots__ = ["id", "type"]
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    type: AssetType
    def __init__(self, type: _Optional[_Union[AssetType, str]] = ..., id: _Optional[str] = ...) -> None: ...

class GetAssetResponse(_message.Message):
    __slots__ = ["asset"]
    ASSET_FIELD_NUMBER: _ClassVar[int]
    asset: AssetDetails
    def __init__(self, asset: _Optional[_Union[AssetDetails, _Mapping]] = ...) -> None: ...

class LookupAssetByCspIDRequest(_message.Message):
    __slots__ = ["account_id", "customer_id", "region", "source_id", "type"]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    CUSTOMER_ID_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    customer_id: str
    region: str
    source_id: str
    type: AssetType
    def __init__(
        self,
        customer_id: _Optional[str] = ...,
        account_id: _Optional[str] = ...,
        region: _Optional[str] = ...,
        type: _Optional[_Union[AssetType, str]] = ...,
        source_id: _Optional[str] = ...,
    ) -> None: ...

class LookupAssetByCspIDResponse(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class SyncAssetsRequest(_message.Message):
    __slots__ = ["account_id", "assets", "region"]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    ASSETS_FIELD_NUMBER: _ClassVar[int]
    REGION_FIELD_NUMBER: _ClassVar[int]
    account_id: str
    assets: _containers.RepeatedCompositeFieldContainer[AffectedAsset]
    region: str
    def __init__(
        self,
        account_id: _Optional[str] = ...,
        region: _Optional[str] = ...,
        assets: _Optional[_Iterable[_Union[AffectedAsset, _Mapping]]] = ...,
    ) -> None: ...

class AssetType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class ActionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
