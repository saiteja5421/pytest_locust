# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: csp/inventory/v1/asset.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from .. import validate_pb2 as validate__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x1c\x63sp/inventory/v1/asset.proto\x12\x10\x63sp.inventory.v1\x1a\x0evalidate.proto"\xa6\x01\n\rAffectedAsset\x12\x39\n\x04type\x18\x01 \x01(\x0e\x32\x1b.csp.inventory.v1.AssetTypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12\x34\n\x06\x61\x63tion\x18\x02 \x01(\x0e\x32\x1c.csp.inventory.v1.ActionTypeR\x06\x61\x63tion\x12$\n\tsource_id\x18\x03 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x08sourceId"\x96\x01\n\x11SyncAssetsRequest\x12\'\n\naccount_id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\taccountId\x12\x1f\n\x06region\x18\x02 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x06region\x12\x37\n\x06\x61ssets\x18\x03 \x03(\x0b\x32\x1f.csp.inventory.v1.AffectedAssetR\x06\x61ssets"\x8f\x01\n\x0c\x41ssetDetails\x12\x39\n\x04type\x18\x01 \x01(\x0e\x32\x1b.csp.inventory.v1.AssetTypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12*\n\x11payload_mime_type\x18\x02 \x01(\tR\x0fpayloadMimeType\x12\x18\n\x07payload\x18\x03 \x01(\x0cR\x07payload"f\n\x0fGetAssetRequest\x12\x39\n\x04type\x18\x01 \x01(\x0e\x32\x1b.csp.inventory.v1.AssetTypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12\x18\n\x02id\x18\x02 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id"H\n\x10GetAssetResponse\x12\x34\n\x05\x61sset\x18\x01 \x01(\x0b\x32\x1e.csp.inventory.v1.AssetDetailsR\x05\x61sset"\x82\x02\n\x19LookupAssetByCspIDRequest\x12:\n\x0b\x63ustomer_id\x18\x01 \x01(\tB\x19\xfa\x42\x16r\x14\x32\x0f(?i)^[0-9a-f]+$\x98\x01 R\ncustomerId\x12\'\n\naccount_id\x18\x02 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\taccountId\x12\x1f\n\x06region\x18\x03 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x06region\x12\x39\n\x04type\x18\x04 \x01(\x0e\x32\x1b.csp.inventory.v1.AssetTypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12$\n\tsource_id\x18\x05 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x08sourceId"6\n\x1aLookupAssetByCspIDResponse\x12\x18\n\x02id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id"\xee\x01\n\x0e\x41ssetStateInfo\x12\x39\n\x04type\x18\x01 \x01(\x0e\x32\x1b.csp.inventory.v1.AssetTypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12\x18\n\x02id\x18\x02 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id\x12\x46\n\x05state\x18\x03 \x01(\x0e\x32&.csp.inventory.v1.AssetStateInfo.StateB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x05state"?\n\x05State\x12\x15\n\x11STATE_UNSPECIFIED\x10\x00\x12\x0c\n\x08STATE_OK\x10\x01\x12\x11\n\rSTATE_DELETED\x10\x02*_\n\tAssetType\x12\x1a\n\x16\x41SSET_TYPE_UNSPECIFIED\x10\x00\x12\x1f\n\x1b\x41SSET_TYPE_MACHINE_INSTANCE\x10\x01\x12\x15\n\x11\x41SSET_TYPE_VOLUME\x10\x02*[\n\nActionType\x12\x1b\n\x17\x41\x43TION_TYPE_UNSPECIFIED\x10\x00\x12\x17\n\x13\x41\x43TION_TYPE_CREATED\x10\x01\x12\x17\n\x13\x41\x43TION_TYPE_DELETED\x10\x02\x42#Z!csp/inventory/v1;csp_inventory_v1b\x06proto3'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "csp.inventory.v1.asset_pb2", globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b"Z!csp/inventory/v1;csp_inventory_v1"
    _AFFECTEDASSET.fields_by_name["type"]._options = None
    _AFFECTEDASSET.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _AFFECTEDASSET.fields_by_name["source_id"]._options = None
    _AFFECTEDASSET.fields_by_name["source_id"]._serialized_options = b"\372B\004r\002\020\001"
    _SYNCASSETSREQUEST.fields_by_name["account_id"]._options = None
    _SYNCASSETSREQUEST.fields_by_name["account_id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _SYNCASSETSREQUEST.fields_by_name["region"]._options = None
    _SYNCASSETSREQUEST.fields_by_name["region"]._serialized_options = b"\372B\004r\002\020\001"
    _ASSETDETAILS.fields_by_name["type"]._options = None
    _ASSETDETAILS.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _GETASSETREQUEST.fields_by_name["type"]._options = None
    _GETASSETREQUEST.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _GETASSETREQUEST.fields_by_name["id"]._options = None
    _GETASSETREQUEST.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["customer_id"]._options = None
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name[
        "customer_id"
    ]._serialized_options = b"\372B\026r\0242\017(?i)^[0-9a-f]+$\230\001 "
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["account_id"]._options = None
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["account_id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["region"]._options = None
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["region"]._serialized_options = b"\372B\004r\002\020\001"
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["type"]._options = None
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["source_id"]._options = None
    _LOOKUPASSETBYCSPIDREQUEST.fields_by_name["source_id"]._serialized_options = b"\372B\004r\002\020\001"
    _LOOKUPASSETBYCSPIDRESPONSE.fields_by_name["id"]._options = None
    _LOOKUPASSETBYCSPIDRESPONSE.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _ASSETSTATEINFO.fields_by_name["type"]._options = None
    _ASSETSTATEINFO.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _ASSETSTATEINFO.fields_by_name["id"]._options = None
    _ASSETSTATEINFO.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _ASSETSTATEINFO.fields_by_name["state"]._options = None
    _ASSETSTATEINFO.fields_by_name["state"]._serialized_options = b"\372B\005\202\001\002 \000"
    _ASSETTYPE._serialized_start = 1270
    _ASSETTYPE._serialized_end = 1365
    _ACTIONTYPE._serialized_start = 1367
    _ACTIONTYPE._serialized_end = 1458
    _AFFECTEDASSET._serialized_start = 67
    _AFFECTEDASSET._serialized_end = 233
    _SYNCASSETSREQUEST._serialized_start = 236
    _SYNCASSETSREQUEST._serialized_end = 386
    _ASSETDETAILS._serialized_start = 389
    _ASSETDETAILS._serialized_end = 532
    _GETASSETREQUEST._serialized_start = 534
    _GETASSETREQUEST._serialized_end = 636
    _GETASSETRESPONSE._serialized_start = 638
    _GETASSETRESPONSE._serialized_end = 710
    _LOOKUPASSETBYCSPIDREQUEST._serialized_start = 713
    _LOOKUPASSETBYCSPIDREQUEST._serialized_end = 971
    _LOOKUPASSETBYCSPIDRESPONSE._serialized_start = 973
    _LOOKUPASSETBYCSPIDRESPONSE._serialized_end = 1027
    _ASSETSTATEINFO._serialized_start = 1030
    _ASSETSTATEINFO._serialized_end = 1268
    _ASSETSTATEINFO_STATE._serialized_start = 1205
    _ASSETSTATEINFO_STATE._serialized_end = 1268
# @@protoc_insertion_point(module_scope)
