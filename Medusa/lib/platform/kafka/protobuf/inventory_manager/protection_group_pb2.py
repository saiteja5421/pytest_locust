# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: csp/inventory/v1/protection_group.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import asset_pb2 as csp_dot_inventory_dot_v1_dot_asset__pb2
from .. import validate_pb2 as validate__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\'csp/inventory/v1/protection_group.proto\x12\x10\x63sp.inventory.v1\x1a\x1c\x63sp/inventory/v1/asset.proto\x1a\x0evalidate.proto"^\n\x16ProtectionGroupDetails\x12*\n\x11payload_mime_type\x18\x01 \x01(\tR\x0fpayloadMimeType\x12\x18\n\x07payload\x18\x02 \x01(\x0cR\x07payload"5\n\x19GetProtectionGroupRequest\x12\x18\n\x02id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id"q\n\x1aGetProtectionGroupResponse\x12S\n\x10protection_group\x18\x01 \x01(\x0b\x32(.csp.inventory.v1.ProtectionGroupDetailsR\x0fprotectionGroup"9\n\x1dResolveProtectionGroupRequest\x12\x18\n\x02id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id"\xad\x01\n\x1eResolveProtectionGroupResponse\x12S\n\x10protection_group\x18\x01 \x01(\x0b\x32(.csp.inventory.v1.ProtectionGroupDetailsR\x0fprotectionGroup\x12\x36\n\x06\x61ssets\x18\x02 \x03(\x0b\x32\x1e.csp.inventory.v1.AssetDetailsR\x06\x61ssetsB#Z!csp/inventory/v1;csp_inventory_v1b\x06proto3'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "csp.inventory.v1.protection_group_pb2", globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b"Z!csp/inventory/v1;csp_inventory_v1"
    _GETPROTECTIONGROUPREQUEST.fields_by_name["id"]._options = None
    _GETPROTECTIONGROUPREQUEST.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _RESOLVEPROTECTIONGROUPREQUEST.fields_by_name["id"]._options = None
    _RESOLVEPROTECTIONGROUPREQUEST.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _PROTECTIONGROUPDETAILS._serialized_start = 107
    _PROTECTIONGROUPDETAILS._serialized_end = 201
    _GETPROTECTIONGROUPREQUEST._serialized_start = 203
    _GETPROTECTIONGROUPREQUEST._serialized_end = 256
    _GETPROTECTIONGROUPRESPONSE._serialized_start = 258
    _GETPROTECTIONGROUPRESPONSE._serialized_end = 371
    _RESOLVEPROTECTIONGROUPREQUEST._serialized_start = 373
    _RESOLVEPROTECTIONGROUPREQUEST._serialized_end = 430
    _RESOLVEPROTECTIONGROUPRESPONSE._serialized_start = 433
    _RESOLVEPROTECTIONGROUPRESPONSE._serialized_end = 606
# @@protoc_insertion_point(module_scope)
