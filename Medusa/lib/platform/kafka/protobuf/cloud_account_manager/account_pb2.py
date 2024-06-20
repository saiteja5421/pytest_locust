# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: csp/cloudaccountmanager/v1/account.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from .. import validate_pb2 as validate__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n(csp/cloudaccountmanager/v1/account.proto\x12\x1a\x63sp.cloudaccountmanager.v1\x1a\x1fgoogle/protobuf/timestamp.proto\x1a\x0evalidate.proto"\x9f\x06\n\x0e\x43spAccountInfo\x12\x18\n\x02id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\x02id\x12\x1b\n\x04name\x18\x02 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x04name\x12\x37\n\x13service_provider_id\x18\x03 \x01(\tB\x07\xfa\x42\x04r\x02\x10\x01R\x11serviceProviderId\x12S\n\x06status\x18\x04 \x01(\x0e\x32\x31.csp.cloudaccountmanager.v1.CspAccountInfo.StatusB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x06status\x12M\n\x04type\x18\x05 \x01(\x0e\x32/.csp.cloudaccountmanager.v1.CspAccountInfo.TypeB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x04type\x12\x16\n\x06paused\x18\x06 \x01(\x08R\x06paused\x12r\n\x11validation_status\x18\x07 \x01(\x0e\x32;.csp.cloudaccountmanager.v1.CspAccountInfo.ValidationStatusB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x10validationStatus\x12\x1e\n\ngeneration\x18\x08 \x01(\x03R\ngeneration"j\n\x06Status\x12\x16\n\x12STATUS_UNSPECIFIED\x10\x00\x12\x15\n\x11STATUS_REGISTERED\x10\x01\x12\x17\n\x13STATUS_UNREGISTERED\x10\x02\x12\x18\n\x14STATUS_UNREGISTERING\x10\x03"J\n\x04Type\x12\x14\n\x10TYPE_UNSPECIFIED\x10\x00\x12\x0c\n\x08TYPE_AWS\x10\x01\x12\x0e\n\nTYPE_AZURE\x10\x02\x12\x0e\n\nTYPE_MS365\x10\x03"\x94\x01\n\x10ValidationStatus\x12!\n\x1dVALIDATION_STATUS_UNSPECIFIED\x10\x00\x12!\n\x1dVALIDATION_STATUS_UNVALIDATED\x10\x01\x12\x1c\n\x18VALIDATION_STATUS_PASSED\x10\x02\x12\x1c\n\x18VALIDATION_STATUS_FAILED\x10\x03"\xeb\x04\n\x0f\x41\x63\x63ountSyncInfo\x12\'\n\naccount_id\x18\x01 \x01(\tB\x08\xfa\x42\x05r\x03\xb0\x01\x01R\taccountId\x12j\n\x0e\x61sset_category\x18\x02 \x01(\x0e\x32\x39.csp.cloudaccountmanager.v1.AccountSyncInfo.AssetCategoryB\x08\xfa\x42\x05\x82\x01\x02 \x00R\rassetCategory\x12R\n\x0elast_synced_at\x18\x03 \x01(\x0b\x32\x1a.google.protobuf.TimestampB\x10\xfa\x42\r\xb2\x01\n\x08\x01*\x06\x08\x80\xb3\xbe\x8e\x06R\x0clastSyncedAt\x12\x66\n\x10last_sync_status\x18\x04 \x01(\x0e\x32\x32.csp.cloudaccountmanager.v1.AccountSyncInfo.StatusB\x08\xfa\x42\x05\x82\x01\x02 \x00R\x0elastSyncStatus"\x9b\x01\n\rAssetCategory\x12\x1e\n\x1a\x41SSET_CATEGORY_UNSPECIFIED\x10\x00\x12.\n*ASSET_CATEGORY_MACHINE_INSTANCE_AND_VOLUME\x10\x01\x12\x1b\n\x17\x41SSET_CATEGORY_DATABASE\x10\x02\x12\x1d\n\x19\x41SSET_CATEGORY_KUBERNETES\x10\x03"i\n\x06Status\x12\x16\n\x12STATUS_UNSPECIFIED\x10\x00\x12\r\n\tSTATUS_OK\x10\x01\x12\x12\n\x0eSTATUS_WARNING\x10\x02\x12\x10\n\x0cSTATUS_ERROR\x10\x03\x12\x12\n\x0eSTATUS_UNKNOWN\x10\x04\x42\x37Z5csp/cloudaccountmanager/v1;csp_cloudaccountmanager_v1b\x06proto3'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "csp.cloudaccountmanager.v1.account_pb2", globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    DESCRIPTOR._serialized_options = b"Z5csp/cloudaccountmanager/v1;csp_cloudaccountmanager_v1"
    _CSPACCOUNTINFO.fields_by_name["id"]._options = None
    _CSPACCOUNTINFO.fields_by_name["id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _CSPACCOUNTINFO.fields_by_name["name"]._options = None
    _CSPACCOUNTINFO.fields_by_name["name"]._serialized_options = b"\372B\004r\002\020\001"
    _CSPACCOUNTINFO.fields_by_name["service_provider_id"]._options = None
    _CSPACCOUNTINFO.fields_by_name["service_provider_id"]._serialized_options = b"\372B\004r\002\020\001"
    _CSPACCOUNTINFO.fields_by_name["status"]._options = None
    _CSPACCOUNTINFO.fields_by_name["status"]._serialized_options = b"\372B\005\202\001\002 \000"
    _CSPACCOUNTINFO.fields_by_name["type"]._options = None
    _CSPACCOUNTINFO.fields_by_name["type"]._serialized_options = b"\372B\005\202\001\002 \000"
    _CSPACCOUNTINFO.fields_by_name["validation_status"]._options = None
    _CSPACCOUNTINFO.fields_by_name["validation_status"]._serialized_options = b"\372B\005\202\001\002 \000"
    _ACCOUNTSYNCINFO.fields_by_name["account_id"]._options = None
    _ACCOUNTSYNCINFO.fields_by_name["account_id"]._serialized_options = b"\372B\005r\003\260\001\001"
    _ACCOUNTSYNCINFO.fields_by_name["asset_category"]._options = None
    _ACCOUNTSYNCINFO.fields_by_name["asset_category"]._serialized_options = b"\372B\005\202\001\002 \000"
    _ACCOUNTSYNCINFO.fields_by_name["last_synced_at"]._options = None
    _ACCOUNTSYNCINFO.fields_by_name[
        "last_synced_at"
    ]._serialized_options = b"\372B\r\262\001\n\010\001*\006\010\200\263\276\216\006"
    _ACCOUNTSYNCINFO.fields_by_name["last_sync_status"]._options = None
    _ACCOUNTSYNCINFO.fields_by_name["last_sync_status"]._serialized_options = b"\372B\005\202\001\002 \000"
    _CSPACCOUNTINFO._serialized_start = 122
    _CSPACCOUNTINFO._serialized_end = 921
    _CSPACCOUNTINFO_STATUS._serialized_start = 588
    _CSPACCOUNTINFO_STATUS._serialized_end = 694
    _CSPACCOUNTINFO_TYPE._serialized_start = 696
    _CSPACCOUNTINFO_TYPE._serialized_end = 770
    _CSPACCOUNTINFO_VALIDATIONSTATUS._serialized_start = 773
    _CSPACCOUNTINFO_VALIDATIONSTATUS._serialized_end = 921
    _ACCOUNTSYNCINFO._serialized_start = 924
    _ACCOUNTSYNCINFO._serialized_end = 1543
    _ACCOUNTSYNCINFO_ASSETCATEGORY._serialized_start = 1281
    _ACCOUNTSYNCINFO_ASSETCATEGORY._serialized_end = 1436
    _ACCOUNTSYNCINFO_STATUS._serialized_start = 1438
    _ACCOUNTSYNCINFO_STATUS._serialized_end = 1543
# @@protoc_insertion_point(module_scope)